# Copyright (c) 2021 SUSE Software Solutions Germany GmbH.  All rights reserved.
#
# This file is part of kiwi-obs-plugin.
#
# kiwi-obs-plugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# kiwi-obs-plugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with kiwi-obs-plugin.  If not, see <http://www.gnu.org/licenses/>
#
import os
import logging
import shutil
from lxml import etree
import requests
from requests.auth import HTTPBasicAuth
from tempfile import NamedTemporaryFile
from typing import (
    Any, Dict, List, NamedTuple, Optional
)

# project
from kiwi.xml_state import XMLState
from kiwi.runtime_config import RuntimeConfig
from kiwi.solver.repository.base import SolverRepositoryBase
from kiwi.system.uri import Uri
from kiwi.command import Command

from kiwi.exceptions import KiwiUriOpenError

from kiwi_obs_plugin.credentials import Credentials

from kiwi_obs_plugin.exceptions import (
    KiwiOBSPluginBuildInfoError,
    KiwiOBSPluginProjectError,
    KiwiOBSPluginSourceError,
    KiwiOBSPluginCredentialsError
)

git_source_type = NamedTuple(
    'git_source_type', [
        ('clone', str),
        ('revision', str),
        ('source_dir', str),
        ('use_entire_source_dir', bool),
        ('files', List[str])
    ]
)

obs_checkout_type = NamedTuple(
    'obs_checkout_type', [
        ('checkout_dir', str),
        ('profile', Optional[str])
    ]
)

obs_repo_status_type = NamedTuple(
    'obs_repo_status_type', [
        ('flag', str),
        ('message', str)
    ]
)

log: Any = logging.getLogger('kiwi')


class OBS:
    """
    **Implements methods to access the Open Build Service API**
    """
    def __init__(
        self, image_path: str, ssl_verify: bool = True,
        user: Optional[str] = None, password: Optional[str] = None
    ):
        """
        Initialize OBS API access for a given project and package

        :param str image_path: OBS project/package path
        :param str user: OBS account user name
        :param str password: OBS account password
        """
        runtime_config = RuntimeConfig()
        try:
            (self.project, self.package) = image_path.split(os.sep)
        except ValueError:
            raise KiwiOBSPluginProjectError(
                f'Invalid image path: {image_path}'
            )
        if not password:
            for credentials in runtime_config.get_obs_api_credentials() or []:
                if not user:
                    # Use first user/credentials from config
                    (user, password) = list(credentials.items())[0]
                    break
                elif user in credentials:
                    # Use credentials for given user
                    password = credentials.get(user)
                    break
        if not user:
            raise KiwiOBSPluginCredentialsError(
                'No username to access the Open Build Service provided'
            )
        if not password:
            credentials_interactive = Credentials()
            password = credentials_interactive.get_obs_credentials(
                user
            )
        self.user = user
        self.password = password
        self.api_server = runtime_config.get_obs_api_server_url()
        self.ssl_verify = ssl_verify or True

    def fetch_obs_image(
        self, checkout_dir: str, force: bool = False, profile: list = None
    ) -> obs_checkout_type:
        """
        Fetch image description from the obs project

        :param str checkout_dir:
            directory to use for checkout, the directory will be
            created if it does not exist
        :param bool force:
            allow to override existing checkout_dir content

        :return: checkout_dir

        :rtype: str
        """
        log.info('Checking out OBS project:')
        primary_multibuild_profile = profile[0] if profile else None
        if os.path.exists(checkout_dir) and not force:
            raise KiwiOBSPluginSourceError(
                f'OBS source checkout dir: {checkout_dir!r} already exists'
            )
        log.info(f'{self.project}/{self.package}')
        package_link = os.sep.join(
            [
                self.api_server, 'source',
                self.project, self.package
            ]
        )
        request = self._create_request(package_link)
        package_source_xml_tree = OBS._import_xml_request(request)
        package_source_contents = package_source_xml_tree.getroot().xpath(
            '/directory/entry'
        )
        if not package_source_contents:
            raise KiwiOBSPluginSourceError(
                f'OBS source for {self.package!r} package is empty'
            )
        Command.run(
            ['mkdir', '-p', checkout_dir]
        )
        source_files = []
        for entry in package_source_contents:
            source_files.append(entry.get('name'))

        for source_file in source_files:
            log.info(f'--> {source_file}')
            request = self._create_request(
                os.sep.join([package_link, source_file])
            )
            with open(os.sep.join([checkout_dir, source_file]), 'wb') as fd:
                fd.write(request.content)

        if '_service' in source_files:
            self._resolve_git_source_service(checkout_dir)

        if '_multibuild' in source_files and not primary_multibuild_profile:
            primary_multibuild_profile = self._get_primary_multibuild_profile(
                checkout_dir
            )
        return obs_checkout_type(
            checkout_dir=checkout_dir,
            profile=primary_multibuild_profile
        )

    def add_obs_repositories(
        self, xml_state: XMLState, profile: Optional[str] = None,
        arch: str = 'x86_64', repo: str = 'images'
    ) -> Dict[str, obs_repo_status_type]:
        """
        Add repositories from the obs project to the provided XMLState

        :param XMLState xml_state: XMLState object reference
        :param str arch: OBS architecture, defaults to: 'x86_64'
        :param str repo:
            OBS image package build repository name, defaults to: 'images'
        """
        repository_status_report: Dict[str, obs_repo_status_type] = {}
        if not OBS._delete_obsrepositories_placeholder_repo(xml_state):
            # The repo list does not contain the obsrepositories flag
            # Therefore it's not needed to look for repos in the OBS
            # project configuration
            return repository_status_report

        package_name = self.package if not profile \
            else f'{self.package}:{profile}'
        log.info(f'Using OBS repositories from {self.project}/{package_name}')
        buildinfo_link = os.sep.join(
            [
                self.api_server, 'build', self.project, repo, arch,
                package_name, '_buildinfo'
            ]
        )
        request = self._create_request(buildinfo_link)
        buildinfo_xml_tree = OBS._import_xml_request(request)
        repo_paths = buildinfo_xml_tree.getroot().xpath(
            '/buildinfo/path'
        )
        if not repo_paths:
            raise KiwiOBSPluginBuildInfoError(
                f'OBS buildinfo for {package_name} has no repo paths'
            )
        repo_prio_ascending = 0
        repo_prio_descending = 501
        repo_alias = None
        for repo_path in repo_paths:
            repo_url = repo_path.get('url')
            if not repo_url:
                repo_url = 'obs://{0}/{1}'.format(
                    repo_path.get('project'), repo_path.get('repository')
                )
            if repo_url:
                try:
                    repo_uri = Uri(repo_url)
                    repo_url = repo_uri.translate(
                        check_build_environment=False
                    )
                    request = requests.get(repo_url)
                    request.raise_for_status()
                except Exception as issue:
                    repository_status_report[repo_url] = obs_repo_status_type(
                        flag='unreachable', message=f'ignored:{issue}'
                    )
                    continue

                repo_check = SolverRepositoryBase(repo_uri)
                repo_type = repo_check.get_repo_type()
                if not repo_type:
                    repository_status_report[repo_url] = obs_repo_status_type(
                        flag='repo_type_unknown',
                        message='ignored:Unknown repository type'
                    )
                    continue

                if repo_type == 'rpm-md':
                    repo_prio_ascending += 1
                    repo_prio = repo_prio_ascending
                else:
                    repo_prio_descending -= 1
                    repo_prio = repo_prio_descending

                repository_status_report[repo_url] = obs_repo_status_type(
                    flag='ok', message='imported'
                )
                xml_state.add_repository(
                    repo_url, repo_type, repo_alias, f'{repo_prio}'
                )
        return repository_status_report

    @staticmethod
    def print_repository_status(
        repository_status_report: Dict[str, obs_repo_status_type]
    ) -> None:
        there_are_issues = False
        if obs_repo_status_type:
            log.info(
                'Following repositories will be used to build the image:'
            )
            for repo, status in repository_status_report.items():
                if status.flag == 'ok':
                    log.info(f'--> {repo}')
                else:
                    there_are_issues = True
        if there_are_issues:
            log.warn('Repository issues exists')
            if not log.getLogLevel() == logging.DEBUG and not log.get_logfile():
                log.warn('--> Please re-run with --debug for details')
            else:
                for repo, status in repository_status_report.items():
                    if not status.flag == 'ok':
                        log.debug(f'Issue with repository: {repo}')
                        log.debug(f'--> {status.message}')

    @staticmethod
    def write_kiwi_config_from_state(
        xml_state: XMLState, config_file: str
    ) -> None:
        with open(config_file, 'w', encoding='utf-8') as config:
            config.write('<?xml version="1.0" encoding="utf-8"?>')
            config.write(os.linesep)
            xml_state.xml_data.export(
                outfile=config, level=0
            )

    @staticmethod
    def _delete_obsrepositories_placeholder_repo(xml_state):
        """
        Delete repository sections which uses the obsrepositories
        placeholder repo and keep the rest for the configured profiles

        :return:
            Returns True if a placeholder repo got deleted
            otherwise False

        :rtype: bool
        """
        has_obsrepositories = False
        repository_sections_to_keep = []
        repository_sections = xml_state.get_repository_sections()
        for xml_repo in repository_sections:
            repo_source = xml_repo.get_source().get_path()
            if 'obsrepositories' in repo_source:
                has_obsrepositories = True
            else:
                repository_sections_to_keep.append(xml_repo)
        xml_state.xml_data.set_repository(repository_sections_to_keep)
        return has_obsrepositories

    @staticmethod
    def _import_xml_request(request):
        download = NamedTemporaryFile()
        with open(download.name, 'wb') as request_info:
            request_info.write(request.content)
        return etree.parse(download.name)

    @staticmethod
    def _resolve_git_source_service(checkout_dir):
        log.info('Looking up git source service...')
        git_sources: List[git_source_type] = []
        service_xml = etree.parse(
            os.sep.join([checkout_dir, '_service'])
        )
        scm_services = service_xml.getroot().xpath(
            '/services/service[@name="obs_scm"]'
        )
        for scm_service in scm_services:
            source_files: List[str] = []
            (source_ok, source_url, source_dir, source_branch, full_source) = (
                False, None, '', 'master', False
            )
            for param in scm_service:
                scm_type = param.get('name')
                if scm_type == 'scm':
                    source_ok = True if param.text == 'git' else False
                if scm_type == 'url':
                    source_url = param.text
                if scm_type == 'subdir':
                    source_dir = param.text
                if scm_type == 'revision':
                    source_branch = param.text
                if scm_type == 'extract':
                    source_files.append(param.text)
                if scm_type == 'filename':
                    full_source = True
            if source_ok and source_url:
                git_sources.append(
                    git_source_type(
                        clone=source_url,
                        revision=source_branch,
                        source_dir=source_dir,
                        files=source_files,
                        use_entire_source_dir=full_source
                    )
                )
        for git_source in git_sources:
            git_checkout_dir = os.sep.join([checkout_dir, '_obs_scm_git'])
            if not os.path.exists(git_checkout_dir):
                log.info(f'Cloning git: {git_source.clone!r}')
                Command.run(
                    [
                        'git', 'clone', '--branch', git_source.revision,
                        git_source.clone, git_checkout_dir
                    ]
                )
            if git_source.files or git_source.use_entire_source_dir:
                log.info(f'Fetching from {git_source.source_dir!r}')
                for source_file in git_source.files:
                    log.info(f'--> {source_file!r}')
                    shutil.copy(
                        os.sep.join(
                            [
                                git_checkout_dir, git_source.source_dir,
                                source_file
                            ]
                        ), checkout_dir
                    )
                if git_source.use_entire_source_dir:
                    log.info('--> Copy of directory')
                    Command.run(
                        [
                            'cp', '-a', os.sep.join(
                                [git_checkout_dir, git_source.source_dir]
                            ), checkout_dir
                        ]
                    )

    @staticmethod
    def _get_primary_multibuild_profile(checkout_dir):
        log.info('Reading multibuild profile(s)...')
        multibuild_profile = None
        multibuild_xml = etree.parse(
            os.sep.join([checkout_dir, '_multibuild'])
        )
        multibuild_profile_list = multibuild_xml.getroot().xpath(
            '/multibuild/flavor'
        )
        if multibuild_profile_list:
            multibuild_profile = multibuild_profile_list[0].text
            log.info(
                f'--> Using profile {multibuild_profile!r}'
            )
        return multibuild_profile

    def _create_request(self, url):
        try:
            request = requests.get(
                url, auth=HTTPBasicAuth(self.user, self.password),
                verify=self.ssl_verify
            )
            request.raise_for_status()
        except Exception as issue:
            raise KiwiUriOpenError(
                f'{type(issue).__name__}: {issue}'
            )
        return request

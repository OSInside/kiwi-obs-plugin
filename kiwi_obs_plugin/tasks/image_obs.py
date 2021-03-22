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
"""
usage: kiwi-ng image obs -h | --help
       kiwi-ng image obs --image=<path> --target-dir=<directory>
           [--force]
           [--user=<name>]
           [--ssl-no-verify]
           [--arch=<arch>]
           [--repo=<repo>]
       kiwi-ng image obs help


commands:
    obs
        checkout an OBS image build project and adapt it
        for local build capabilities

options:
    --arch=<arch>
        Optional architecture reference for the specifified image
        image. This defaults to x86_64

    --force
        Allow to override existing content from --target-dir

    --image=<project_package_path>
        Image location for an image description in the Open Build Service.
        The specification consists out of the project and package name
        specified like a storage path, e.g `OBS:project:name/package`

    --repo=<repo>
        Optional repository name. This defaults to: image

    --ssl-no-verify
        Do not verify SSL server certificate when connecting to OBS

    --target-dir=<directory>
        the target directory to store the image description checked
        out from OBS and adapted by kiwi to be build locally

    --user=<name>
        Open Build Service account user name. KIWI will ask for the
        user credentials which blocks stdin until entered
"""
import logging
from kiwi.tasks.base import CliTask
from kiwi.help import Help

from kiwi_obs_plugin.obs import OBS

log = logging.getLogger('kiwi')


class ImageObsTask(CliTask):
    def process(self) -> None:
        self.manual = Help()
        if self.command_args.get('help'):
            return self.manual.show('kiwi::image::obs')

        if self.command_args.get('--image'):
            ssl_verify = bool(
                self.command_args['--ssl-no-verify']
            )
            self.obs = OBS(
                self.command_args['--image'], ssl_verify,
                self.command_args['--user']
            )
            obs_checkout = self.obs.fetch_obs_image(
                self.command_args['--target-dir'],
                self.command_args['--force'],
                self.global_args['--profile']
            )
            if obs_checkout.profile:
                self.global_args['--profile'] = [obs_checkout.profile]
            self.load_xml_description(
                obs_checkout.checkout_dir
            )
            repo_status = self.obs.add_obs_repositories(
                self.xml_state, obs_checkout.profile,
                self.command_args['--arch'] or 'x86_64',
                self.command_args['--repo'] or 'images'
            )
            self.obs.write_kiwi_config_from_state(
                self.xml_state, self.config_file
            )
            self.obs.print_repository_status(repo_status)
            log.info('Successfully checked out OBS project at:')
            log.info(f'--> {obs_checkout.checkout_dir}')

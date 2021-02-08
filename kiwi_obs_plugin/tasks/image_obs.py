# Copyright (c) 2021 SUSE Software Solutions Germany GmbH.  All rights reserved.
#
# This file is part of kiwi-obs-build.
#
# kiwi-obs-build is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# kiwi-obs-build is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with kiwi-obs-build.  If not, see <http://www.gnu.org/licenses/>
#
"""
usage: kiwi-ng image obs -h | --help
       kiwi-ng image obs --image=<path> --user=<name> --target-dir=<directory>
           [--arch=<arch>]
           [--repo=<repo>]
           [--ssl-no-verify]
       kiwi-ng image obs help


commands:
    obs
        checkout an OBS image build project and adapt it
        for local build capabilities

options:
    --image=<project_package_path>
        Image location for an image description in the Open Build Service.
        The specification consists out of the project and package name
        specified like a storage path, e.g `OBS:project:name/package`

    --user=<name>
        Open Build Service account user name. KIWI will ask for the
        user credentials which blocks stdin until entered

    --arch=<arch>
        Optional architecture reference for the specifified image
        image. This defaults to x86_64

    --repo=<repo>
        Optional repository name. This defaults to: image

    --obs-ssl-no-verify
        Do not verify SSL server certificate when connecting to OBS

    --target-dir=<directory>
        the target directory to store the image description checked
        out from OBS and adapted by kiwi to be build locally
"""
import logging
import os
from docopt import docopt
from kiwi.tasks.base import CliTask
from kiwi.help import Help


log = logging.getLogger('kiwi')


class ImageObsTask(CliTask):
    def process(self):
        self.manual = Help()
        if self.command_args.get('help') is True:
            return self.manual.show('kiwi::image::obs')

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
from kiwi.exceptions import KiwiError


class KiwiOBSPluginBuildInfoError(KiwiError):
    """
    Exception raised if the OBS buildinfo request did not provide
    the expected information
    """


class KiwiOBSPluginProjectError(KiwiError):
    """
    Exception raised if the given OBS project/package path is
    not a path with two elements separated by the linux path
    delimiter(/)
    """


class KiwiOBSPluginSourceError(KiwiError):
    """
    Exception raised if the OBS image sources cannot be used
    for building the image
    """


class KiwiOBSPluginCredentialsError(KiwiError):
    """
    Exception raised if the the OBS credentials setup failed
    """

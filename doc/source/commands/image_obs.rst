kiwi-ng image obs
=================

SYNOPSIS
--------

.. code:: bash

   kiwi-ng [global options] service <command> [<args>]

   kiwi-ng image obs -h | --help
   kiwi-ng image obs --image=<path> --user=<name> --target-dir=<directory>
       [--arch=<arch>]
       [--repo=<repo>]
       [--ssl-no-verify]
   kiwi-ng image obs help

DESCRIPTION
-----------

Checkout an image managed in the Open Build Service (OBS).
The buildservice allows to store KIWI image descriptions
and builds them on demand. Building such an image description
outside of the buildservice is usually not possible out of
the box. One reason is for example the repository setup which
can be disconnected from the image description and part of the
project configuration in OBS. Another pitfall is the dependency
resolution of packages which is done differently in OBS compared
to the standard resolver from a package manager.

The obs command extension works on top of the image description
in OBS and resolves the issues that prevents a user from building
this description locally with KIWI directly. Please note depending
on how the project is setup in OBS KIWI might not be able to
resolve all issues but still provides a description that serves
as a better base to be build locally compared to the data
stored in OBS.

When calling the obs command the path to an image in OBS must
be provided. This information consists out of the `project`
name in OBS and the `package` name inside of that project which
provides the actual KIWI image description. This information
is provided as a path setting: `project/package` with the
`--image` argument. For the obs command to work the OBS account
`--user` name and the `--target-dir` to store the checked out
image description must be provided too. The user name is used
to create a request to the OBS API server and this request requires
the user to enter its account credentials. KIWI asks for this
credentials via stdin and therefore blocks until entered.

The connection to the OBS server download and API location can
be configured via a custom KIWI configuration file below the `obs`
section as the following example shows:

.. code:: yaml

   obs:
     - public: true
     - download_url: http://download.opensuse.org/repositories
     - api_url: https://api.opensuse.org

The provided information from above represent the default values
used by KIWI. A custom config file can be provided via the
global `--config` option

OPTIONS
-------

--image=<project_package_path>

  Image location for an image description in the Open Build Service.
  The specification consists out of the project and package name
  specified like a storage path, e.g `OBS:project:name/package`

--user=<name>

  Open Build Service account user name. KIWI will ask for the
  user credentials which blocks stdin until entered

--arch=<arch>

  Optional architecture reference for the specifified `--image`
  image. This defaults to `x86_64`

--repo=<repo>

  Optional repository name. In OBS a package build is connected
  to a repository name. This repository name groups a collection
  of software repositories to be used for the package build
  process. If the package build is a KIWI image build this
  repository name defaults to `images`. As the name can be
  set to any custom name, it's only required to specify the
  used repository name if another than the OBS default
  name is used.

--ssl-no-verify

  Dont't verify SSL server certificate when connecting to OBS

--target-dir=<directory>

  the target directory to store the image description checked
  out from OBS and adapted by kiwi to be build locally

EXAMPLE
-------

.. code:: bash

   $ kiwi-ng image obs \
       --image openSUSE:Leap:15.2:Images/livecd-openSUSE --user my_user \
       --target-dir /tmp/livecd-openSUSE

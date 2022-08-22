# ceph-devstack
A tool for testing [Ceph](https://github.com/ceph/ceph) locally using [nested rootless podman containers](https://www.redhat.com/sysadmin/podman-inside-container)


## Overview
ceph-devstack is a tool that can deploy and manage containerized versions of [teuthology](https://github.com/ceph/teuthology) and its associated services, to test Ceph (or just teuthology) on your local machine. It lets you avoid:

- Accessing Ceph's [Sepia lab](https://wiki.sepia.ceph.com/)
- Needing dedicated storage devices to test Ceph OSDs

## Requirements
Mainly, podman 4.0+. This was initially developed on CentOS 9.Stream, but a recent Fedora ought to work as well. Ubuntu doesn't currently ship a new enough podman.
MacOS is a special case as all podman operations are done inside a CoreOS VM; it is not functional as of yet.

## Setup

    $ sudo usermod -a -G disk $(whoami)  # and re-login afterward
    $ git clone -b ceph-devstack https://github.com/ceph/teuthology/
    $ cd teuthology && ./bootstrap
    $ source ./virtualenv/bin/activate
    $ python3 -m pip install git+https://github.com/zmc/ceph-devstack.git

## Usage

    $ export TEUTHOLOGY_SUITE=orch:cephadm:smoke-small
    $ ceph-devstack build && ceph-devstack create && ceph-devstack start
    $ podman logs -f teuthology  # to watch as jobs run
    $ ceph-devstack remove  # when finished

Note:

- `ceph-devstack` currently must be run from within the root directory of a `teuthology` repo.
- By default, we run the `teuthology:no-ceph` suite to self-test teuthology. In the above case, we want to test Ceph itself, so we use the `TEUTHOLOGY_SUITE` environment variable to specify a different one.

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
Note: `ceph-devstack` currently must be run from within the root directory of a `teuthology` repo.

First, you'll want to build all the containers:

    $ ceph-devstack build

Next, you can start them with:

    $ ceph-devstack start

Once everything is started, a message similar to this will be logged:

`View test results at http://smithi065.front.sepia.ceph.com:8081/`

This link points to the running Pulpito instance. Test archives are also stored in the `--data-dir` (default: `~/.local/share/ceph-devstack`).

To watch teuthology's output, you can:

    $ podman logs -f teuthology

If you want testnode containers to be replaced as they are stopped and destroyed, you can:

    $ ceph-devstack watch

When finished, this command removes all the resources that were created:

    $ ceph-devstack remove

### Specifying a Test Suite
By default, we run the `teuthology:no-ceph` suite to self-test teuthology. If we wanted to test Ceph itself, we could use the `orch:cephadm:smoke-small` suite:

    $ export TEUTHOLOGY_SUITE=orch:cephadm:smoke-small

### Testnode Count
We default to providing three testnode containers. If you want more, you can:

    $ ceph-devstack create --testnode-count N

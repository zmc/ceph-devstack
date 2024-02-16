# ceph-devstack
A tool for testing [Ceph](https://github.com/ceph/ceph) locally using [nested rootless podman containers](https://www.redhat.com/sysadmin/podman-inside-container)

## Overview
ceph-devstack is a tool that can deploy and manage containerized versions of [teuthology](https://github.com/ceph/teuthology) and its associated services, to test Ceph (or just teuthology) on your local machine. It lets you avoid:

- Accessing Ceph's [Sepia lab](https://wiki.sepia.ceph.com/)
- Needing dedicated storage devices to test Ceph OSDs

It is currently under active development and has not yet had a formal release.

## Supported Operating Systems

☑︎ CentOS 9.Stream should work out of the box

☑︎ CentOS 8.Stream mostly works - but has not yet passed a Ceph test

☐ A recent Fedora should work but has not been tested

☒ Ubuntu does not currently ship a new enough podman

☒ MacOS will require special effort to support since podman operations are done inside a VM

## Requirements

* A supported operating system
* podman 4.0+ using the `crun` runtime.
  * On CentOS 8, modify `/etc/containers/containers.conf` to set the runtime
* Linux kernel 5.12+, or 4.15+ _and_ `fuse-overlayfs`
* cgroup v2
  * On CentOS 8, see [./docs/cgroup_v2.md](./docs/cgroup_v2.md)
* podman's DNS plugin, from the `podman-plugins` package
* A user account that has `sudo` access and also is a member of the `disk` group
* The following sysctl settings:
  * `fs.aio-max-nr=1048576`
  * `kernel.pid_max=4194304`
* If using SELinux in enforcing mode:
  * `setsebool -P container_manage_cgroup=true`
  * `setsebool -P container_use_devices=true`

`ceph-devstack doctor` will check the above and report any issues.

## Setup

```bash
sudo usermod -a -G disk $(whoami)  # and re-login afterward
git clone https://github.com/ceph/teuthology/
cd teuthology && ./bootstrap
python3 -m venv venv
source ./venv/bin/activate
python3 -m pip install git+https://github.com/zmc/ceph-devstack.git
```

## Configuration
`ceph-devstack` 's default configuration is [here](./ceph_devstack/config.yml). It can be extended by placing a file at `~/.config/ceph-devstack/config.yml` or by using the `--config-file` flag.

`ceph-devstack show-conf` will output the current configuration.

As an example, the following configuration will use a local image for paddles with the tag `TEST`; it will also create ten testnode containers; and will build its teuthology container from the git repo at `~/src/teuthology`:
```
containers:
  paddles:
    image: localhost/paddles:TEST
  testnode:
    count: 10
  teuthology:
    repo: ~/src/teuthology
```
## Usage
By default, pre-built container images are pulled from [quay.io/ceph-infra](https://quay.io/organization/ceph-infra). The images can be overridden via the config file. It's also possible to _build_ images from on-disk git repositories.

First, you'll want to pull all the images:

```bash
ceph-devstack pull
```

Optional: If building any images from repos:
```bash
ceph-devstack build
```

Next, you can start the containers with:

```bash
ceph-devstack start
```

Once everything is started, a message similar to this will be logged:

`View test results at http://smithi065.front.sepia.ceph.com:8081/`

This link points to the running Pulpito instance. Test archives are also stored in the `--data-dir` (default: `~/.local/share/ceph-devstack`).

To watch teuthology's output, you can:

```bash
podman logs -f teuthology
```

If you want testnode containers to be replaced as they are stopped and destroyed, you can:

```bash
ceph-devstack watch
```

When finished, this command removes all the resources that were created:

```bash
ceph-devstack remove
```

### Specifying a Test Suite
By default, we run the `teuthology:no-ceph` suite to self-test teuthology. If we wanted to test Ceph itself, we could use the `orch:cephadm:smoke-small` suite:

```bash
export TEUTHOLOGY_SUITE=orch:cephadm:smoke-small
```

It's possible to skip the automatic suite-scheduling behavior:

```bash
export TEUTHOLOGY_SUITE=none
```

### Using testnodes from an existing lab
If you need to use "real" testnodes and have access to a lab, there are a few additonal steps to take. We will use the Sepia lab as an example below:

To give the teuthology container access to your SSH private key (via `podman secret`):

```bash
export SSH_PRIVKEY_PATH=$HOME/.ssh/id_rsa
```

To lock machines from the lab:

```bash
ssh teuthology.front.sepia.ceph.com
~/teuthology/virtualenv/bin/teuthology-lock \
  --lock-many 1 \
  --machine-type smithi \
  --desc "teuthology dev testing"
```

Once you have your machines locked, you need to provide a list of their hostnames and their machine type:

```bash
export TEUTHOLOGY_TESTNODES="smithiXXX.front.sepia.ceph.com,smithiYYY.front.sepia.ceph.com"
export TEUTHOLOGY_MACHINE_TYPE="smithi"
```

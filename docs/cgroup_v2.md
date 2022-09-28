# Enabling cgroup v2

If `/sys/fs/cgroup/cgroup.controllers` is present, cgroup v2 is enabled. If not, enabling will require adding an argument to the kernel command line. On CentOS 8.Stream, it can be enabled by:

* `$ sudo grubby --update-kernel=ALL --args='systemd.unified_cgroup_hierarchy=1'`
* Then, reboot the system

## Issues on CentOS 8

See [Red Hat bz#1897579](https://bugzilla.redhat.com/show_bug.cgi?id=1897579) and the Red Hat Knowledge Base article [podman run fails on RHEL8 with cgroup v2](https://access.redhat.com/solutions/6964319) for details. Until it is fixed, it's necessary to do the following:

    $ sudo mkdir -p /etc/systemd/system/{user@.service.d,user-.slice.d}
    $ sudo tee /etc/systemd/system/user@.service.d/delegate.conf > /dev/null <<-EOF
    [Service]
    Delegate=memory pids cpu cpuset
    EOF
    $ sudo tee /etc/systemd/system/user-.slice.d/override.conf > /dev/null <<-EOF
    [Slice]
    Slice=user.slice
    CPUAccounting=yes
    MemoryAccounting=yes
    IOAccounting=yes
    TasksAccounting=yes
    EOF
    $ sudo systemctl daemon-reload

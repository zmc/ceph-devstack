pipeline {
  agent { node {
    label "centos9 && x86_64"
  }}
  environment {
    CDS_CONF = "${env.WORKSPACE}/ceph-devstack.yml"
  }
  stages {
    stage("Setup system") {
      steps {
        script {
          env.OLD_AIO_MAX_NR = """${sh(returnStdout: true, script: "sysctl -b fs.aio-max-nr")}"""
        }
        sh """
          sudo dnf install -y podman podman-plugins python3-virtualenv policycoreutils-devel selinux-policy-devel
          sudo sysctl fs.aio-max-nr=1048576
          sudo usermod -a -G disk ${env.USER}
          # The below command is not idempotent, hence the '|| true'.
          # See https://patchwork.kernel.org/project/selinux/patch/20240214122706.522873-1-vmojzis@redhat.com/
          sudo semanage fcontext -a -e /var/lib/containers ~/.local/share/containers || true
          sudo restorecon -R ~/.local/share/containers
          sudo setsebool -P container_manage_cgroup=true
          sudo setsebool -P container_use_devices=true
          cd ${env.WORKSPACE}/ceph_devstack
          make -f /usr/share/selinux/devel/Makefile ceph_devstack.pp
          sudo semodule -i ceph_devstack.pp
        """
      }
    }
    stage("Clone teuthology") {
      steps {
        sh """
        git clone -b ${env.TEUTHOLOGY_BRANCH} https://github.com/ceph/teuthology ${env.WORKSPACE}/teuthology
        """
      }
    }
    stage("Setup ceph-devstack") {
      steps {
        sh """
          python3 -V
          python3 -m venv venv
          source ./venv/bin/activate
          python -V
          pip3 install -U pip
          pip3 install -e .
          if [ -z ${env.TEUTHOLOGY_BRANCH} ]; then
            python3 -c "import yaml; print(yaml.safe_dump({'data_dir': '${env.WORKSPACE}/data'}))" > ${env.CDS_CONF}
          else
            python3 -c "import yaml; print(yaml.safe_dump({'containers': {'teuthology': {'repo': '${env.WORKSPACE}/teuthology'}}, 'data_dir': '${env.WORKSPACE}/data'}))" > ${env.CDS_CONF}
          fi
          ceph-devstack --config-file ${env.CDS_CONF} show-conf
          ceph-devstack --config-file ${env.CDS_CONF} doctor
        """
      }
    }
    stage("Build containers") {
      steps {
        sh """
          source ./venv/bin/activate
          ceph-devstack -v --config-file ${env.CDS_CONF} build
        """
      }
    }
    stage("Create containers") {
      steps {
        sh """
          source ./venv/bin/activate
          ceph-devstack --config-file ${env.CDS_CONF} -v create
        """
      }
    }
    stage("Start containers") {
      steps {
        sh """
          source ./venv/bin/activate
          ceph-devstack --config-file ${env.CDS_CONF} -v start
        """
      }
    }
    stage("Wait for teuthology container") {
      steps {
        sh """
          podman wait teuthology
          exit \$(podman inspect -f "{{.State.ExitCode}}" teuthology)
        """
      }
    }
  }
  post {
    always {
      sh """
        podman logs teuthology
      """
      sh """
        mkdir -p data/containers
        podman logs teuthology 2>&1 > data/containers/teuthology.log
        source ./venv/bin/activate
        ceph-devstack --config-file ${env.CDS_CONF} -v remove
        podman volume prune -f
        podman ps -a
        sudo sysctl fs.aio-max-nr=${env.OLD_AIO_MAX_NR}
      """
      archiveArtifacts artifacts: 'ceph-devstack.yml,data/archive/**', fingerprint: true
    }
  }
}

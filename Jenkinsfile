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
          sudo dnf install -y podman podman-plugins python3-virtualenv
          sudo sysctl fs.aio-max-nr=1048576
          sudo setsebool -P container_manage_cgroup true
        """
      }
    }
    stage("Setup ceph-devstack") {
      steps {
        sh """
          python3 -m venv venv
          source ./venv/bin/activate
          python3 -V
          python3 -m venv venv
          source ./venv/bin/activate
          python -V
          pip3 install -U pip
          pip3 install -e .
          ceph-devstack doctor
          echo "data_dir: ${env.WORKSPACE}/data" > ${env.CDS_CONF}
          echo "teuthology_repo: ${env.WORKSPACE}/teuthology" >> ${env.CDS_CONF}
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

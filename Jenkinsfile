pipeline {
  agent { label 'subman' }
  stages {
    // stage('prepare') {steps {echo 'prepare'}}
    stage('Test') {
      parallel {
        stage('stylish') {
          agent { label 'subman-centos7' }
          steps { sh readFile(file: 'jenkins/stylish-tests.sh') }
        }
        stage('tito') {
          agent { label 'rpmbuild' }
          steps { sh readFile(file: 'jenkins/tito-tests.sh') }
        }
        stage('RHEL7 unit') {
          agent { label 'subman-centos7' }
          steps {
            // echo "skipping for debug..."
            sh readFile(file: 'jenkins/nose-tests.sh')
            junit('nosetests.xml')
            // publishCoverage('coverage.xml')
            }
        }
        // TODO: figure if this is needed and implement
        // stage('RHEL8 unit') {steps {echo 'nose'}}
        stage('Fedora unit') {
          steps {
            sh readFile(file: 'jenkins/python3-tests.sh')
            junit('nosetests.xml')
            // TODO: find the correct adapter or generate coverage tests that can be
            //       parsed by an existing adapter:
            //       https://plugins.jenkins.io/code-coverage-api/
            // publishCoverage adapters: [jacocoAdapter('coverage.xml')]
          }
        }
        stage('opensuse42') {
          agent { label 'opensuse42' }
          steps { sh readFile(file: 'jenkins/suse-tests.sh') }
        }
        // stage('sles11') {
        //   // FIXME:  sles11 can't be tested due missing python deps (incl. nose)
        // }
        stage('sles12') {
          agent { label 'sles12' }
          steps { sh readFile(file: 'jenkins/suse-tests.sh') }
        }
        // TODO: add after QE creates pipeline
        // stage('Functional') {
        //   stages{
        //     stage('Build RPM') {steps {echo 'Build RPM'}}
        //     stage('Prepare') {steps {echo 'Prepare'}}
        //     stage('Provision') {steps {echo 'Provisioning'}}
        //     stage('Tier 1') {steps {echo 'Tier 1'}}
        //   }
        // }
      }
    }
    stage('SUSE Builds') {
      matrix {
        axes {
          axis {
            name 'PLATFORM'
            values 'openSUSE_Leap_42.2', 'SLE_12_SP1', 'SLE_11_SP4'
          }
        }
        stages {
          stage('Build') {
            agent { label 'opensuse42' }
            steps {
              sh "scripts/suse_build.sh 'home:kahowell' ${PLATFORM}"
              // sh """
              // if [ -d python-rhsm ]; then
              //   cd python-rhsm
              //   ../scripts/suse_build.sh 'home:kahowell' ${PLATFORM} -k \$WORKSPACE
              //   cd ..
              // fi
              // """
            }
          }
        }
      }
    }
  // stage('cleanup') {steps {echo 'cleanup'}}
  }
}
pipeline {
  agent { label 'subman' }
  stages {
    // stage('prepare') {steps {echo 'prepare'}}
    stage('Test') {
      parallel {
        stage('Python 2 stylish') {
          agent { label 'subman-centos7' }
          steps {
            sh readFile(file: 'jenkins/stylish-tests.sh')
          }
        }
        stage('Fedora tito') {
          agent { label 'rpmbuild' }
          steps { sh readFile(file: 'jenkins/tito-tests.sh') }
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
//         stage('OpenSuSE 15') {
//           agent { label 'opensuse15' }
//           steps { sh readFile(file: 'jenkins/suse-tests.sh') }
//         }
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
//     stage('SUSE Builds') {
//       matrix {
//         axes {
//           axis {
//             name 'PLATFORM'
//             values 'openSUSE_Leap_15.2'
//           }
//         }
//         stages {
//           stage('Build') {
//             agent { label 'opensuse15' }
//             steps {
//               sh "scripts/suse_build.sh 'home:kahowell' ${PLATFORM}"
//             }
//           }
//         }
//       }
//     }
  // stage('cleanup') {steps {echo 'cleanup'}}
  }
}
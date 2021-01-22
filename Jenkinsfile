pipeline {
  agent { label 'subman' }
  stages {
    stage('Python 3 stylish') {
      steps {
        sh readFile(file: 'jenkins/python3-stylish-tests.sh')
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

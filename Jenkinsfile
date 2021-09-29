pipeline {
  agent { label 'subman' }
  options {
    timeout(time: 10, unit: 'MINUTES')
  }
  stages {
    // stage('prepare') {steps {echo 'prepare'}}
    stage('Test') {
      parallel {
        stage('Python stylish') {
          steps {
            sh readFile(file: 'jenkins/python3-stylish-tests.sh')
          }
        }
        stage('Fedora tito') {
          agent { label 'rpmbuild' }
          steps { sh readFile(file: 'jenkins/tito-tests.sh') }
        }
        stage('Fedora unit') {
          steps {
            sh readFile(file: 'jenkins/python3-tests.sh')
            junit('coverage.xml')
            // TODO: find the correct adapter or generate coverage tests that can be
            //       parsed by an existing adapter:
            //       https://plugins.jenkins.io/code-coverage-api/
            // publishCoverage adapters: [jacocoAdapter('coverage.xml')]
          }
        }
        // Unit tests of libdnf plugins
        stage('Libdnf unit') {
          steps {
            sh readFile(file: 'jenkins/libdnf-tests.sh')
          }
        }
      }
    }
  }
}

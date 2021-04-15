pipeline {
  agent { label 'subman' }
  options {
    timeout(time: 10, unit: 'MINUTES')
  }
  stages {
    stage('Test') {
      parallel {
        stage('Python stylish') {
          steps {
            sh readFile(file: 'jenkins/python3-stylish-tests.sh')
          }
        }
        stage('tito') {
          agent { label 'rpmbuild' }
          steps { sh readFile(file: 'jenkins/tito-tests.sh') }
        }
        stage('RHEL 8 unit') {
          steps {
            sh readFile(file: 'jenkins/python3-tests.sh')
            junit('nosetests.xml')
            // TODO: find the correct adapter or generate coverage tests that can be
            //       parsed by an existing adapter:
            //       https://plugins.jenkins.io/code-coverage-api/
            // publishCoverage adapters: [jacocoAdapter('coverage.xml')]
          }
        }
      }
    }
  // stage('cleanup') {steps {echo 'cleanup'}}
  }
}

pipeline {
  agent { label 'subman' }
  stages {
    stage('Test') {
      parallel {
        stage('stylish') {
          agent { label 'subman-centos7' }
          steps { sh readFile(file: 'jenkins/stylish-tests.sh') }
        }
        stage('tito') {
          agent { label 'subman-centos7' }
          steps { sh readFile(file: 'jenkins/tito-tests.sh') }
        }
        stage('RHEL7 unit') {
          agent { label 'subman-centos7' }
          steps {
            sh readFile(file: 'jenkins/nose-tests.sh')
            junit('nosetests.xml')
            }
        }
      }
    }
  }
}

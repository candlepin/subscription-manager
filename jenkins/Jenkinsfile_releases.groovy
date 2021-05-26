pipeline {
  agent { label 'rpmbuild' }
  options {
    timeout(time: 10, unit: 'MINUTES')
  }
  stages {
    stage('Release') {
      steps {
          sh readFile(file: 'jenkins/release.sh')
      }
    }
  }
}


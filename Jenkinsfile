pipeline {
  agent { label 'subman' }
  stages {
    stage('prepare') {steps {echo 'prepare'}}
    stage('test') {
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
          steps { sh readFile(file: 'jenkins/nose-tests.sh') }
        }
        stage('RHEL8 unit') {steps {echo 'nose'}}
        stage('Fedora unit') {
          steps { sh readFile(file: 'jenkins/python3-tests.sh') }
        }
        stage('opensuse42') {
          stages {
            stage('build') {steps {echo 'tito'}}
            stage('nose') {steps {echo 'nose'}}
          }
        }
        stage('sles12') {
          stages {
            stage('build') {steps {echo 'tito'}}
            stage('nose') {steps {echo 'nose'}}
          }
        }
        stage('Functional') {
          stages{
            stage('Build RPM') {steps {echo 'Build RPM'}}
            stage('Prepare') {steps {echo 'Prepare'}}
            stage('Provision') {steps {echo 'Provisioning'}}
            stage('Tier 1') {steps {echo 'Tier 1'}}
          }
        }
      }
    }
  stage('cleanup') {steps {echo 'cleanup'}}
  }
}
pipeline {
  agent { label 'subman' }
  stages {
    // stage('prepare') {steps {echo 'prepare'}}
    stage('Test') {
      parallel {
        stage('stylish') {
          agent { label 'subman' }
          steps { sh readFile(file: 'jenkins/stylish-tests.sh') }
        }
        stage('tito') {
          agent { label 'rpmbuild' }
          steps { sh readFile(file: 'jenkins/tito-tests.sh') }
        }
        // TODO: figure if this is needed and implement
        // stage('RHEL8 unit') {steps {echo 'nose'}}
        stage('unit') {
          steps {
            sh readFile(file: 'jenkins/python3-tests.sh')
            junit('nosetests.xml')
            // TODO: find the correct adapter or generate coverage tests that can be
            //       parsed by an existing adapter:
            //       https://plugins.jenkins.io/code-coverage-api/
            // publishCoverage adapters: [jacocoAdapter('coverage.xml')]
          }
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
  }
}

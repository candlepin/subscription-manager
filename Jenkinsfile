pipeline {
  agent { label 'subman' }
  options {
    timeout(time: 10, unit: 'MINUTES')
  }
  stages {
    stage('Build Container') {
      environment {
        QUAY_CREDS=credentials('candlepin-quay-bot')
      }
      steps {
        sh './containers/build_and_push.sh'
      }
    }
    stage('Test') {
      parallel {
        stage('stylish') {
          steps {
            sh (
              script: './jenkins/toolbox-run.sh stylish jenkins/stylish.sh',
              returnStatus: false
            )
          }
        }
        stage('tito') {
          steps {
            sh (
              script: './jenkins/toolbox-run.sh tito jenkins/tito.sh',
              returnStatus: true
            )
          }
        }
        // TODO: figure if this is needed and implement
        // stage('RHEL8 unit') {steps {echo 'nose'}}
        stage('unit') {
          steps {
            sh (
              script: './jenkins/toolbox-run.sh unit jenkins/unit.sh',
              returnStatus: true
            )
            junit('nosetests.xml')
            // TODO: find the correct adapter or generate coverage tests that can be
            //       parsed by an existing adapter:
            //       https://plugins.jenkins.io/code-coverage-api/
            // publishCoverage adapters: [jacocoAdapter('coverage.xml')]
          }
        }
        // Unit tests of libdnf plugins
        stage('libdnf') {
          steps {
            sh (
              script: './jenkins/toolbox-run.sh libdnf jenkins/libdnf.sh',
              returnStatus: true
            )
          }
        }
      }
    }
  }
}

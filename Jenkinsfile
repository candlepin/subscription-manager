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
        sh readFile(file: 'containers/build_and_push.sh')
      }
    }
    stage('Test') {
      parallel {
        stage('stylish') {
          steps {
            sh './jenkins/toolbox-run.sh stylish jenkins/stylish.sh'
          }
        }
        stage('tito') {
          steps {
            sh './jenkins/toolbox-run.sh tito jenkins/tito.sh'
          }
        }
        // TODO: figure if this is needed and implement
        // stage('RHEL8 unit') {steps {echo 'nose'}}
        stage('unit') {
          steps {
            sh './jenkins/toolbox-run.sh unit jenkins/unit.sh'
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
            sh './jenkins/toolbox-run.sh libdnf jenkins/libdnf.sh'
          }
        }
      }
    }
  }
}

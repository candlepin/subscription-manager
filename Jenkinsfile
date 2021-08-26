pipeline {
  agent { label 'subman' }
  options {
    timeout(time: 15, unit: 'MINUTES')
  }
  environment {
    REGISTRY_URL = 'quay.io/candlepin'
    GIT_HASH = sh(returnStdout: true, script: "git rev-parse HEAD").trim()
    PODMAN_USERNS = 'keep-id'
  }
  stages {
    stage('Build Container') {
      environment {
        QUAY_CREDS = credentials('candlepin-quay-bot')
      }
      steps {
        sh('./scripts/build_and_push.sh')
      }
    }
    stage('Test') {
      parallel {
        stage('stylish') {
          agent { label 'subman' }
          steps {
            sh('./jenkins/run.sh stylish jenkins/stylish.sh')
          }
        }
        stage('tito') {
          steps {
            sh('./jenkins/run.sh tito jenkins/tito.sh')
          }
        }
        stage('unit') {
          steps {
            sh('./jenkins/run.sh unit jenkins/unit.sh')
          }
          post {
            always {
              archiveArtifacts allowEmptyArchive: true, artifacts: 'coverage.xml', fingerprint: true
              // https://www.jenkins.io/doc/pipeline/steps/cobertura/
              step([$class: 'CoberturaPublisher',
                            autoUpdateHealth: false,
                            autoUpdateStability: false,
                            coberturaReportFile: 'coverage.xml',
                            failNoReports: false,
                            failUnhealthy: false,
                            failUnstable: false,
                            maxNumberOfBuilds: 10,
                            onlyStable: false,
                            sourceEncoding: 'ASCII',
                            zoomCoverageChart: false])
              // https://www.jenkins.io/doc/pipeline/steps/junit/
              junit allowEmptyResults: true, keepLongStdio: true, skipMarkingBuildUnstable: true, skipPublishingChecks: true, testResults: 'coverage.xml'
            }
          }
        }
        // Unit tests of libdnf plugins
        stage('libdnf') {
          steps {
            sh('./jenkins/run.sh libdnf jenkins/libdnf.sh')
          }
        }
      }
    }
  }
}

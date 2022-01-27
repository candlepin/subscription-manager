pipeline {
  agent { label 'subman' }
  options {
    timeout(time: 10, unit: 'MINUTES')
  }
  stages {
    stage('Test') {
      parallel {
        stage('stylish') {
          steps {
            sh('./jenkins/stylish.sh')
          }
        }
        stage('tito') {
          agent { label 'rpmbuild' }
          steps {
            sh('./jenkins/tito.sh')
          }
        }
        stage('unit') {
          steps {
            sh('./jenkins/unit.sh')
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
            sh('./jenkins/libdnf.sh')
          }
        }
      }
    }
  }
}

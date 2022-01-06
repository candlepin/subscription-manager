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
        stage('Fedora tito') {
          agent { label 'rpmbuild' }
          steps { sh readFile(file: 'jenkins/tito-tests.sh') }
        }
        stage('Fedora unit') {
          steps {
            sh readFile(file: 'jenkins/python3-tests.sh')
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
        stage('Libdnf unit') {
          steps {
            sh readFile(file: 'jenkins/libdnf-tests.sh')
          }
        }
      }
    }
  }
}

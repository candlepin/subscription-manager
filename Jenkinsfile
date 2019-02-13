pipeline {
    agent { label 'rhsm' }
    parameters {
        booleanParam(name: 'RUN_NOSETESTS', defaultValue: true, description: 'Should we run the nose tests?')
        booleanParam(name: 'RUN_PYTHON3_NOSETESTS', defaultValue: true, description: 'Should we run the python 3 nose tests?')
        booleanParam(name: 'RUN_STYLISH_TESTS', defaultValue: true, description: 'Should we run the python 3 nose tests?')
    }
    stages {
        stage('Parallel stage') {
            parallel {
                stage('Nose tests') {
                    agent { label 'rhsm' }
                    options {
                        timeout(time: 5, unit: 'MINUTES')
                    }
                    when { expression { return params.RUN_NOSETESTS } }
                    steps {
                        sh readFile('scripts/jenkins/subscription-manager-nose-tests.sh')
                        sh readFile('scripts/jenkins/python-rhsm-nose-tests.sh')
                        sh readFile('scripts/jenkins/syspurpose-nose-tests.sh')
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'nosetests.xml', onlyIfSuccessful: false, allowEmptyArchive: true
                            archiveArtifacts artifacts: 'coverage.xml', onlyIfSuccessful: false, allowEmptyArchive: true
                            archiveArtifacts artifacts: 'python-rhsm/nosetests.xml', onlyIfSuccessful: false, allowEmptyArchive: true
                            archiveArtifacts artifacts: 'syspurpose/nosetests.xml', onlyIfSuccessful: false, allowEmptyArchive: true
                            archiveArtifacts artifacts: 'syspurpose/coverage.xml', onlyIfSuccessful: false, allowEmptyArchive: true
                            publishHTML([allowMissing: true,
                                         alwaysLinkToLastBuild: false,
                                         keepAll: false,
                                         reportDir: 'cover/',
                                         reportFiles: 'index.html',
                                         reportName: 'Coverage module html report',
                                         reportTitles: ''])
                            publishHTML([allowMissing: true,
                                         alwaysLinkToLastBuild: false,
                                         keepAll: false,
                                         reportDir: 'python-rhsm/htmlcov/',
                                         reportFiles: 'index.html',
                                         reportName: 'python-rhsm coverage module html report',
                                         reportTitles: ''])
                            publishHTML([allowMissing: true,
                                         alwaysLinkToLastBuild: false,
                                         keepAll: false,
                                         reportDir: 'htmlcov/',
                                         reportFiles: 'index.html',
                                         reportName: 'python-rhsm coverage module html report',
                                         reportTitles: ''])
                            publishHTML([allowMissing: true,
                                         alwaysLinkToLastBuild: false,
                                         keepAll: false,
                                         reportDir: 'syspurpose/htmlcov/',
                                         reportFiles: 'index.html',
                                         reportName: 'syspurpose coverage module html report',
                                         reportTitles: ''])
                        }
                    }
                }
                stage('Python 3 Nose Tests') {
                    agent { label 'rhsm' }
                    options {
                        timeout(time: 5, unit: 'MINUTES')
                    }
                    when { expression { return params.RUN_PYTHON3_NOSETESTS } }
                    steps {
                        sh readFile('scripts/jenkins/subscription-manager-python3-tests.sh')
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'nosetests.xml', onlyIfSuccessful: false, allowEmptyArchive: true
                            publishHTML([allowMissing: true,
                                         alwaysLinkToLastBuild: false,
                                         keepAll: false,
                                         reportDir: 'htmlcov/',
                                         reportFiles: 'index.html',
                                         reportName: 'Coverage module html report',
                                         reportTitles: ''])
                        }
                    }
                }
                stage('Stylish') {
                    agent { label 'rhsm' }
                    options {
                        timeout(time: 5, unit: 'MINUTES')
                    }
                    when { expression { return params.RUN_STYLISH_TESTS } }
                    steps {
                        sh readFile('scripts/jenkins/subscription-manager-stylish-tests.sh')
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'stylish_results.txt', onlyIfSuccessful: false, allowEmptyArchive: true
                        }
                    }
                }
                stage('AHHA') {
                    steps {
                        sh "echo lololol"
                    }
                }
            }
        }
    }
}

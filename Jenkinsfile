pipeline {
    agent any

    stages {

        stage('Clone Repo') {
            steps {
                git 'https://github.com/sohamgaurav5305/loanflow.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t loanflow-app .'
            }
        }

        stage('Deploy to LoanFlow Server') {
            steps {
                sshagent(['loanflow-ssh']) {
                    sh '''
                    ssh -o StrictHostKeyChecking=no ec2-user@<LOANFLOW_IP> "
                        docker stop loanflow || true &&
                        docker rm loanflow || true &&
                        docker run -d -p 5000:5000 --name loanflow loanflow-app
                    "
                    '''
                }
            }
        }
    }
}

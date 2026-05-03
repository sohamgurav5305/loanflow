pipeline {
    agent any

    environment {
        APP_NAME = "loanflow-app"
        CONTAINER_NAME = "loanflow"
    }

    stages {
        stage('Clone') {
            steps {
                git 'https://github.com/sohamgurav5305/loanflow'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t loanflow-app .'
            }
        }

        stage('Stop Old Container') {
            steps {
                sh 'docker stop loanflow || true'
                sh 'docker rm loanflow || true'
            }
        }

        stage('Run Container') {
            steps {
                sh 'docker run -d -p 5000:5000 --name loanflow loanflow-app'
            }
        }
    }
}
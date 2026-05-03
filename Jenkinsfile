pipeline {
    agent any

    environment {
        APP_NAME = "loanflow-app"
        CONTAINER_NAME = "loanflow"
        PORT = "5000"
    }

    stages {

        stage('Build Docker Image') {
            steps {
                echo "Building Docker Image..."
                sh 'docker build -t $APP_NAME .'
            }
        }

        stage('Stop Old Container') {
            steps {
                echo "Stopping old container if exists..."
                sh 'docker stop $CONTAINER_NAME || true'
                sh 'docker rm $CONTAINER_NAME || true'
            }
        }

        stage('Run Container') {
            steps {
                echo "Running new container..."
                sh 'docker run -d -p $PORT:5000 --name $CONTAINER_NAME $APP_NAME'
            }
        }

    }

    post {
        success {
            echo "✅ Deployment Successful!"
        }
        failure {
            echo "❌ Deployment Failed!"
        }
    }
}
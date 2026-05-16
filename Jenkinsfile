pipeline{
    agent any

    stages{
        stage('clone repository'){
            steps{
                checkout scm
            }
        }

        stage('build & deploy'){
            steps{
                sh 'docker-compose down -v || true'
                sh 'docker-compose up --build -d'
            }
        }

    }

    post {
        success {
            echo 'Deployment successful!'
        }
        failure {
            echo 'Deployment failed. Please check the logs.'
        }
    }
}
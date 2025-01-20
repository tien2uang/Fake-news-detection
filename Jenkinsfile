pipeline {
    agent any

    environment {
        // Tên ACR
        ACR_NAME   = "fndacr"         // fndacr.azurecr.io
        IMAGE_NAME = "fnd"           // Tên repo image trong ACR
        IMAGE_TAG  = "latest"
    }

    stages {
        stage('Checkout') {
            steps {
                // Lấy code từ Git. Bạn thay repo/branch cho đúng
                git branch: 'main', url: 'https://github.com/tien2uang/Fake-news-detection.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                  echo "Build Docker image..."
                  docker build -t \$ACR_NAME.azurecr.io/\$IMAGE_NAME:\$IMAGE_TAG .
                """
            }
        }

        stage('Login to ACR') {
            steps {
                withCredentials([usernamePassword(credentialsId: '1aa9e638-9ac9-422c-9cef-f1b90cb286ca',
                                                  usernameVariable: 'ACR_USER',
                                                  passwordVariable: 'ACR_PASS')]) {
                    sh """
                      echo "Docker login to ACR..."
                      docker login \$ACR_NAME.azurecr.io -u \$ACR_USER -p \$ACR_PASS
                    """
                }
            }
        }

        stage('Push Image') {
            steps {
                sh """
                  docker push \$ACR_NAME.azurecr.io/\$IMAGE_NAME:\$IMAGE_TAG
                """
            }
        }

        stage('Deploy to AKS') {
            steps {
                // Lấy file kubeconfig từ Jenkins Credentials
                withCredentials([file(credentialsId: 'e1eb7dca-58fd-4717-b0ca-4a39574ccaf1', variable: 'KUBECONFIG_FILE')]) {
                    sh """
                      export KUBECONFIG=\$KUBECONFIG_FILE

                      echo "Apply Kubernetes manifests..."
                      kubectl apply -f deployment.yaml
                      kubectl apply -f service.yaml
                    """
                }
            }
        }
    }

    post {
        always {
            script {
                // (Tuỳ chọn) xóa image cục bộ sau khi xong
                sh "docker rmi \$ACR_NAME.azurecr.io/\$IMAGE_NAME:\$IMAGE_TAG || true"
            }
        }
    }
}

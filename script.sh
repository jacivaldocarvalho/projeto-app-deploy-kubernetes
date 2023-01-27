#!/bin/bash
echo "Criando as imagens!"

docker build -t jncarvalho/projeto-backend:1.0 backend/.
docker build -t jncarvalho/projeto-database:1.0 database/.


echo "Realizando o Push das imagens!"

docker push jncarvalho/projeto-backend:1.0
docker push jncarvalho/projeto-database:1.0

echo "Criando os serviços  no Cluster Kubernetes!"

kubectl apply -f ./services.yml

echo "Criando os deployments!!"

kubectl apply -f ./deployment.yml
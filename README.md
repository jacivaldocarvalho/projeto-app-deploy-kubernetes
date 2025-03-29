# Projeto de deployment de aplicações em um ambiente Kubernetes

Este repositório contém um script que visa facilitar o processo de deployment de aplicações em um ambiente Kubernetes. O objetivo principal é automatizar e simplificar o processo de configuração e implantação, garantindo que qualquer pessoa, independentemente de sua experiência com Kubernetes, consiga realizar o deployment de forma eficiente e sem erros.

---

## Índice

- [Descrição](#descrição)
- [Como Usar](#como-usar)
- [Exemplo de Saída Esperada](#exemplo-de-saída-esperada)
- [Pré-Requisitos](#pré-requisitos)
- [Licença](#licença)
- [Contato](#contato)

---

## Descrição

O **Projeto App Deploy Kubernetes** é uma solução para automatizar o processo de deployment de aplicações em clusters Kubernetes. O script foi projetado para facilitar a criação de pods, deployments, serviços e outras configurações necessárias para a execução de uma aplicação dentro de um ambiente Kubernetes, tornando o processo mais ágil e sem necessidade de configurações manuais complexas.

### Funcionalidade Principal

Este repositório possui um script que realiza as seguintes tarefas:
- Criação de arquivos de configuração para deployments, serviços e volumes no Kubernetes.
- Integração simples com repositórios de imagens Docker, possibilitando o uso de containers preexistentes.
- Implementação de recursos e limites de CPU e memória para os containers.
- Estratégias de deployment para escalabilidade e manutenção de alta disponibilidade.

### Recursos Adicionais
- Suporte a configurações dinâmicas através de variáveis de ambiente.
- Capacidade de integrar com ferramentas de CI/CD, facilitando a automação do processo de deployment em pipelines de produção.

---

## Como Usar

Para utilizar o script de deployment, siga os passos abaixo:

### 1. Clonando o Repositório
Primeiro, clone o repositório para o seu ambiente local:

```bash
git clone https://github.com/jacivaldocarvalho/projeto-app-deploy-kubernetes.git
cd projeto-app-deploy-kubernetes
```

### 2. Instalando as Dependências
Este projeto depende de algumas ferramentas para garantir que o script funcione corretamente. Certifique-se de que você tenha as seguintes ferramentas instaladas:

- **kubectl**: Ferramenta de linha de comando do Kubernetes.
- **Docker**: Necessário para empacotar e gerenciar os containers.
  
Caso não tenha o `kubectl` ou o `Docker` instalados, você pode seguir os guias oficiais para instalação:
- [Instalar kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
- [Instalar Docker](https://docs.docker.com/get-docker/)

### 3. Executando o Script

Com o repositório clonado e as dependências instaladas, você pode rodar o script de deployment. Dependendo do seu caso de uso, o comando pode ser o seguinte:

```bash
bash deploy.sh
```

Esse comando irá iniciar o processo de criação e configuração do ambiente Kubernetes com base nas definições do script.

---

## Exemplo de Saída Esperada

Ao executar o script, você verá a seguinte saída no terminal:

```bash
Iniciando deployment da aplicação...

Criando Deployment...
Deployment 'app-deploy' criado com sucesso!

Criando Serviço...
Serviço 'app-service' configurado com sucesso!

Aplicando configurações do Kubernetes...
Configurações aplicadas com sucesso!

Deployment realizado com sucesso! O aplicativo está disponível em seu cluster Kubernetes.
```

Após o deployment, a aplicação estará disponível dentro do seu ambiente Kubernetes, e você poderá acessá-la via o serviço criado.

---

## Pré-Requisitos

Antes de executar o script, certifique-se de que você possui os seguintes pré-requisitos instalados em seu sistema:

- **Kubernetes** (em um cluster local ou remoto).
- **kubectl** configurado para interagir com seu cluster Kubernetes.
- **Docker** (para trabalhar com imagens de containers).
  
Recomenda-se também que o Kubernetes esteja configurado com permissões adequadas para a criação de pods e serviços, e que você tenha uma imagem Docker disponível em um repositório acessível.

---

## Licença

Este projeto está licenciado sob a **MIT License**. Você pode ver o texto completo da licença abaixo:

---

## Contato

Se você tiver dúvidas ou sugestões, sinta-se à vontade para entrar em contato!

- **LinkedIn** 👔: [Jacivaldo Carvalho](https://www.linkedin.com/in/jacivaldocarvalho/)
- **E-mail** 📧: [jacivaldocarvalho@email.com](mailto:jacivaldocarvalho@email.com)
- **GitHub** 🐙: [jacivaldocarvalho](https://github.com/jacivaldocarvalho)
- **Medium** ✍️: [jacivaldocarvalho](https://medium.com/@jacivaldocarvalho)


# Deploy the site APIs
This README will walk you through how to set up the APIs used by the Gen Studio website:

-  Building an image similarity model using ResNet50 and an approximate nearest neighbors index
-  Create docker containers for the image similarity model, BigGAN and ProGAN Flask APIs
-  Deploy these APIs to [Azure Kubernetes Service (AKS)](https://azure.microsoft.com/en-us/services/kubernetes-service/)

# Build the Image Similarity Model
Follow these steps to build your own image similarity model. 

> Note: these steps assume you have the training images stored in an Azure Blob Storage as jpgs. We have also already normalized all these images to 512x512. We also assume familiarity with Jupyter Notebooks.
1. Navigate to `api/ImageSimilarity/Model`
2. We will use the pre-trained ResNet50 model in Keras for feature extraction in each image. This will convert each 512x512 image into a numerical vector of length 2048. We used the images available on [The MET's Open Access API](https://metmuseum.github.io/). 
    - Start Jupyter Notebooks and open `Featurize Images.ipynb` notebook. (You may need to pip install some of the python packages)
    - Under the **Define Constants** cell, define the url and file paths to the images you will use for the model & where you want the table containing the featurized version of the images saved.
    - Run the remaining cells. These cells will download each image, run them through the ResNet50 model and then save 3 files: 
        - **preprocessedimages.pkl**: Table containing the featurized image vectors. 
        - **targets.pkl**: A list of the `[name, url]` for each corresponding image in `preprocessedimages.pkl`
        - **failed.pkl**: list of the index in targets of any images we failed to featurize.
        - **total_i.pkl**: decimal count of the total number of images analyzed
    - Shutdown and close the `Featurize Images.ipynb` notebook. 
3. Next, we build a nearest neighbors model using the vector for each image you created in the previous step. This model will be used to search for the closest visually similar image.
    - Open the `Build Nearest Neighbors.ipynb`  notebook
    - Under the **Define Constants** cell, define the file path where the annoy model will be saved & path to the featurized images.
    - Run the remaining cells. These cells will build, train and save the annoy index. 

    ### You have now built your nearest neighbors index! 

# Build the Docker Containers

## Build the image similarity API container
Follow these steps to create a gpu enabled docker container for an image similarity search API. The API calls are defined in `api/ImageSimilarity/deployment/app.py`
1. Navigate to `api/ImageSimilarity/deployment`

2. Copy your `targets.pkl` file and Annoy Index (`annoyIndex2.ann`) which were created in the prior step into the folder

3. If you changed the name for either of these files, you will need to update line 25 of `Dockerfile_gpu`. 

4. Run the following command to build the docker container. If you are not using a GPU machine, use `Dockerfile` instead. 

    ```bash
    docker build -t <tagname> -f Dockerfile_gpu
    ```
5. To test your API, start the docker on port 5000. You can now call this API at `localhost:5000`

    ```bash
    nvidia-docker run -p 5000:5000 imagesimilaritymodel 
    ```

6. Tag and publish your container
    ```bash
    docker tag <container name> <dockerhub username>/<container name>
    docker push <dockerhub username>/<container name>
    ```
    
## Build the BigGAN API container
Follow these steps to build your own API which generates images from BigGAN.
1. Navigate to `api/BigGAN/deployment`
2. Repeat steps 4-6 from **Build the image similarity API container** but update the container name and dockerfile name

## Build the ProGAN API container
Follow these steps to build your own API which generates images from ProGAN.
1. Navigate to `api/ProGAN/deployment`
2. Repeat steps 4-6 from **Build the image similarity API container** but update the container name and dockerfile name


# Deployment
These steps will walk through how to use ASK to deploy the Flask APIs.

## Install Azure CLI and kubectl & Deploy your AKS Cluster
1. [install the Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest). The Azure CLI is a command-line tool for managing Azure resources. 

2. Create a resource group for your AKS cluster
    ```bash
    az group create --name myResourceGroup --location eastus
    ```
3. Create your AKS cluster
    ```bash
        az aks create \
        --resource-group myResourceGroup \
        --name myAKSCluster \
        --node-count 1 \
        --enable-addons monitoring \
        --generate-ssh-keys
    ```
4. Connect to the Kubernetes cluster from your local computer with [kubectl](https://kubernetes.io/docs/reference/kubectl/kubectl/), the Kubernetes command-line client. If you're using the Azure Cloud Shell, `kubectl` is already installed. To install it locally, use the [az aks install-cli](https://docs.microsoft.com/cli/azure/aks#az-aks-install-cli) command:
    ```bash
    az aks install-cli
    ```

5. Connect to the cluster using kubectl. To do this configure `kubectl` to connect to your AKS cluster with the [az aks get-credentials](https://docs.microsoft.com/cli/azure/aks#az-aks-get-credentials) command:
    ```bash
    az aks get-credentials --resource-group myResourceGroup --name myAKSCluster
    ```

6. Verify your connection with the [kubectl get nodes](https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) command:
    ```bash
    $ kubectl get nodes

    NAME                       STATUS   ROLES   AGE     VERSION
    aks-nodepool1-28993262-0   Ready    agent   3m18s   v1.9.11
    ```

## Deploy APIs
1. To deploy the image similarity API, navigate to `api/ImageSimilarity/`

2. Use the [kubectl apply](https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#apply) command to deploy the service:
    ```
    kubectl apply -f BigGAN.yaml
    ```

3. Repeat these 2 steps for the BigGAN and ProGAN apis.

## Check AKS Cluster Status
1. Open your Kubernetes cluster UI with the following command
        
    ```
    az aks browse -g myResourceGroup -n myAKSCluster
    ```

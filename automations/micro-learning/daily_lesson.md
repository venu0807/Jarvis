# Today's Skill: Containerization with Docker

Containerization is an essential concept and tool for modern software development, particularly if you're aiming at roles that demand high-paying skills like a Zoho Developer or Shopify Developer.

## Key Concepts
- **Containers** vs Containers are lightweight packages used to run applications along with their dependencies.
- They encapsulate the application environment (OS, libraries) so it runs consistently across various platforms and cloud providers. 

For example:
```markdown
A Docker container for running a Python app might look something like this:

1. Create your `Dockerfile` specifying how you want everything to be built up.

2. Use an official base image that already includes all the dependencies you'll need.
3. Copy over only what's necessary, build it if required (like compiling some libraries), and run the final command in a minimal environment for efficiency and security reasons.
```

## Why Docker?

1. **Portability**: Ensures your application runs seamlessly anywhere you deploy it without worrying about differences between environments.

2. **Isolation**: Provides isolated execution of applications, making them immune to conflicts caused by different software versions or system configurations.


To illustrate this with a practical example:

### Example Code Snippet
Create an `app.py`:
```python
# app.py

def main():
    print("Hello World!")

if __name__ == "__main__":
    main()
```

Next, create the Dockerfile for your application. You can use something like below to build and run a simple Python container:

#### Create a Dockerfile (Docker)
```dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

COPY app.py .

RUN pip install --no-cache-dir -r requirements.txt  # Assuming you have any dependencies in this file.

CMD ["python", "app.py"]
```

This defines:
- `FROM`: The base image (Python).
- `WORKDIR` to set the working directory inside your container.
- Copying files and installing packages necessary for running a Python application.


## Build & Run Your Docker Container
1. **Build**: Create an image from this Dockerfile:

   ```bash
   docker build -t my-python-app .
   ```

2. **Run**:
   
   ```bash
   docker run --name python-test -d my-python-app
   ```

3. Check if your container is running with `docker ps`.

### Quiz to Test Your Understanding

1. What command do you use in Dockerfile to specify the base image for building an application?

2. How can containers help ensure consistent execution across different environments?
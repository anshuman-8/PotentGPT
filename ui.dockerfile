# Use an official Node.js runtime as the base image
FROM node:14 AS build

# Set the working directory in the container
WORKDIR /app

# Take arguments from the command line
ARG REACT_APP_BACKEND_URL

# Set environment variables
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

# Copy package.json and package-lock.json to the container
COPY ./react-client/package*.json ./

# Install dependencies
RUN npm install

# Copy the entire project directory to the container
COPY ./react-client .

# Build the React app
RUN npm run build

# Use Nginx to serve the built React app
FROM nginx:alpine

# Copy the build files from the previous stage to Nginx's default public directory
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 3000

# Command to run when starting the container
CMD ["nginx", "-g", "daemon off;"]

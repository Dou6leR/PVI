FROM nginx:alpine

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static frontend files to default Nginx root
COPY . /usr/share/nginx/html

# Clean up configuration/docker files from public web directory
RUN rm -f /usr/share/nginx/html/nginx.conf /usr/share/nginx/html/Dockerfile

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

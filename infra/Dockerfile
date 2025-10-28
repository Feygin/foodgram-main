FROM nginx:1.22.1
COPY nginx.conf /etc/nginx/templates/default.conf.template
# Ensure the mount points exist (volumes will overlay)
RUN mkdir -p /static /media
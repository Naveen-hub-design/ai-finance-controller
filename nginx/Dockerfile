FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY finance-controller.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

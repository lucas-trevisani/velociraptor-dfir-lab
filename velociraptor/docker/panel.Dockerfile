FROM node:22-alpine
WORKDIR /app
COPY panel/package.json /app/package.json
RUN npm install
COPY panel /app
CMD ["npm", "run", "dev"]


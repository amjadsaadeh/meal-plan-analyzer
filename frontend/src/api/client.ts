import axios from 'axios'

const client = axios.create({ baseURL: '/api/' })

client.interceptors.request.use(cfg => {
  const match = document.cookie.match(/csrftoken=([^;]+)/)
  if (match) cfg.headers['X-CSRFToken'] = match[1]
  return cfg
})

export default client

from app import create_app

app = create_app()

if __name__ == '__main__':
    # host='0.0.0.0' 允许局域网内其他设备通过服务器IP访问
    app.run(host='0.0.0.0', debug=True, port=5000)

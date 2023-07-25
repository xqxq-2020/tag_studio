from flask import Flask, send_from_directory

app = Flask(__name__)
app.static_folder = 'E:\code'  # 指定静态文件夹的路径


@app.route('/<path:filename>')
def get_static_file(filename):
    return send_from_directory('E:\code', filename)


if __name__ == '__main__':
    app.run(port=8000)  # 指定端口号为 8000

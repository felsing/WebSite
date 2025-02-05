from flask import Flask, render_template, request, redirect, url_for
import subprocess

app = Flask(__name__)

# 默认配置
config = {
    "PHOTOS2": "photos2",
    "GALLERY_ID": "675e7eeab78e5",
    "MAX_NUM": 610,
    "SAVE_PATH": "/mnt/sdb1/1"
}

# 显示表单和当前配置
@app.route('/', methods=['GET', 'POST'])
def index():
    global config
    if request.method == 'POST':
        # 获取表单输入的参数
        config["PHOTOS2"] = request.form['photos2']
        config["GALLERY_ID"] = request.form['gallery_id']
        config["MAX_NUM"] = int(request.form['max_num'])
        config["SAVE_PATH"] = request.form['save_path']
        
        # 生成脚本的命令
        script_command = f"""
        for i in $(seq 1 {config['MAX_NUM']}); do
            curl -s -L "https://img.xchina.store/{config['PHOTOS2']}/{config['GALLERY_ID']}/$(printf "%04d" $i).jpg" \\
                 -o "{config['SAVE_PATH']}/$(printf "%05d" $i).jpg" \\
                 --create-dirs \\
                 -H "Accept: image/*,*/*;q=0.8" \\
                 -H "Connection: keep-alive" \\
                 -H "Accept-Encoding: gzip, deflate, sdch" \\
                 -H "Referer: https://8se.me/photoShow.php?server=2&id={config['GALLERY_ID']}&index=1&pageSize=20" \\
                 -H "Accept-Language: zh-CN,en,en-GB,en-US;q=0.8" \\
                 -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0" \\
                 -k --retry 4
        done
        """
        
        # 写入一个脚本文件
        with open('/app/download_images.sh', 'w') as f:
            f.write(script_command)
        
        # 执行脚本
        subprocess.Popen(['/bin/bash', '/app/download_images.sh'])
        
        return redirect(url_for('index'))
    
    return render_template('index.html', config=config)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100)

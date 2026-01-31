wq_temp_file_choose = ''

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

function checkMovieUrl() {
    const url = window.location.href;
    if (url.indexOf('/v/movie/') !== -1) {
        return true;
    }
    if (url.indexOf('/v/tv/episode/') !== -1) {
        return true;
    }
    if (url.indexOf('/v/other/') !== -1) {
        return true;
    }
    return false;
}


function evaluateXPath(xpath, contextNode = document) {
    const result = [];
    const query = document.evaluate(xpath, contextNode, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);

    for (let i = 0, length = query.snapshotLength; i < length; ++i) {
        result.push(query.snapshotItem(i));
    }

    return result;
}

function fireContentLoadedEventMovie() {
    // console.log('fireContentLoadedEventMovie');

    // 处理多个文件
    let fileParent = evaluateXPath('//*[@id="root"]/div/div[3]/div/div/div[2]/div/div[2]/div[2]/div[1]')[0]
    if (fileParent) {
        const hasAdd = fileParent.getAttribute('has-add-potplayer');
        if (hasAdd !== '1') {
            fileParent.setAttribute('has-add-potplayer', '1');
            for (let i = 0; i < 10; i++) {
                // //*[@id="root"]/div/div[3]/div/div/div[2]/div/div[2]/div[2]/div[1]/button[1]
                let fileBtn = evaluateXPath('//*[@id="root"]/div/div[3]/div/div/div[2]/div/div[2]/div[2]/div[1]/button[' + (i + 1) + ']')[0]
                if (fileBtn) {
                    const hasAdd = fileBtn.getAttribute('has-add-potplayer');
                    if (hasAdd === '1') {
                        continue
                    }
                    fileBtn.setAttribute('has-add-potplayer', '1')
                    fileBtn.addEventListener('click', async function () {
                        wq_temp_file_choose = i
                        // console.log('choose = ', wq_temp_file_choose)
                    })
                }
            }
        }
    }
    var btn = evaluateXPath('//*[@id="root"]/div/div[3]/div/div/div[2]/div/div[2]/div[1]/div[2]/div/div[1]/button')[0]
    if (!btn) {
        // other 页
        btn = evaluateXPath('//*[@id="root"]/div/div[3]/div/div/div[2]/div/div[2]/div[1]/div[1]/div[2]/div[2]/div[1]/button')[0]
    }
//    console.log('fireContentLoadedEventMovie; btn', btn)
    if (btn) {
        const hasAdd = btn.getAttribute('has-add-potplayer');
        if (hasAdd === '1') {
            return
        }
        wq_temp_file_choose = ''

        btn.setAttribute('has-add-potplayer', '1');

        const clonedElement = btn.cloneNode(true);
        // 添加到父元素的末尾
        btn.parentNode.appendChild(clonedElement);

        var btnText = clonedElement.querySelector('span > span > span')
        btnText.innerHTML = 'PotPlayer播放'

        clonedElement.addEventListener('click', async function () {
            const url = window.location.href;
            const lastPart = url.split('/').pop();
            const origin = window.location.origin;
            const hostname = window.location.hostname;
            const token = getCookie('Trim-MC-token')
            // console.log('play file_choose = ', wq_temp_file_choose)
            if (wq_temp_file_choose === null) {
                wq_temp_file_choose = ''
            }

            const formData = new FormData();
            formData.append('item_guid', lastPart);
            formData.append('base_url', origin);
            formData.append('token', token);
            formData.append('hostname', hostname);
            formData.append('file_choose', wq_temp_file_choose);

            const response = await fetch('http://127.0.0.1:5050/movie', {
                method: 'POST',
                body: formData
            });
        })
    }
}

function fireContentLoadedEventLogo() {
    var logo = evaluateXPath('//*[@id="root"]/div/div[1]/div/div[1]/img')[0]
//    console.log('fireContentLoadedEventMovie; logo', logo)
    if (logo) {
        const hasAdd = logo.getAttribute('has-add-wq-link');
        if (hasAdd === '1') {
            return
        }
        logo.setAttribute('has-add-wq-link', '1');

        logo.addEventListener('click', function () {
            const origin = window.location.origin;
            window.location.href = origin + '/v'
        })
    }
}

function fireContentLoadedEventHoverPlayBtn() {
    const url = window.location.href;
    let all = []
    if (url.endsWith('/v')) {
        // 首页 - 继续观看
        all = evaluateXPath('//*[@id="root"]/div/div[4]/div/div/div[2]/div/div[2]/div[2]/div/div')
        let allList = evaluateXPath('//*[@id="root"]/div/div[4]/div/div/div[2]/div/div[2]/div[3]/div')
        for (const list of allList) {
            let listAll = list.querySelectorAll('div.ms-container > div > div')
            if (listAll) {
                for (const listElement of listAll) {
                    all.push(listElement)
                }
            }
        }
    }
    if (url.endsWith('/v/favorite')) {
        // 收藏
        all = evaluateXPath('//*[@id="semiTabPanel1"]/div/div/div[2]/div[2]/div')
    }
    if (url.indexOf('/v/list/') !== -1) {
        // 分类
        all = evaluateXPath('//*[@id="root"]/div/div[4]/div/div/div[2]/div/div[2]/div[2]/div[2]/div')
    }
    if (url.indexOf('/v/library') !== -1) {
        // 媒体库
        all = evaluateXPath('//*[@id="root"]/div/div[4]/div/div/div[2]/div/div[2]/div[2]/div[2]/div');
    }
    if (all) {
        // console.log('all = ', all)
        for (const allElement of all) {
            const hasAdd = allElement.getAttribute('has-add-wq-link');
            if (hasAdd === '1') {
                continue
            }
            allElement.setAttribute('has-add-wq-link', '1');

            let playElement = allElement.querySelector('div > div > div > a')
            if (!playElement) {
                playElement = allElement.querySelector('div > div > a')
            }
            if (!playElement) {
                continue
            }
            let div = playElement.querySelector('div')

            const clonedElement = div.cloneNode(true);
            // 添加到父元素的末尾
            playElement.appendChild(clonedElement);

            let div0 = clonedElement.querySelector('div');
            if (!div0) {
                continue
            }
            div0.addEventListener('click', async function (e) {
                e.preventDefault()

                let type = 'movie'

                const url = playElement.getAttribute('href')
                if (url.indexOf('/tv') !== -1) {
                    type = 'tv'
                }

                const lastPart = url.split('/').pop();
                const origin = window.location.origin;
                const hostname = window.location.hostname;
                const token = getCookie('Trim-MC-token')

                const formData = new FormData();
                if (type === 'tv') {
                    formData.append('season_guid', lastPart);
                } else {
                    formData.append('item_guid', lastPart);
                }
                formData.append('base_url', origin);
                formData.append('token', token);
                formData.append('hostname', hostname);
                formData.append('file_choose', '');

                const response = await fetch('http://127.0.0.1:5050/' + type, {
                    method: 'POST',
                    body: formData
                });
            });
        }
    }
}

setInterval(() => {
    fireContentLoadedEventLogo()
    fireContentLoadedEventHoverPlayBtn()
    if (!checkMovieUrl()) {
        return;
    }
    fireContentLoadedEventMovie()
}, 300)


function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

function checkUrl() {
    const url = window.location.href;
    if (url.indexOf('/v/tv/season/') == -1) {
        return false;
    }
    return true;
}

setInterval(()=>{
    if(!checkUrl()){
        return ;
    }
    fireContentLoadedEvent()
}, 300)


function evaluateXPath(xpath, contextNode = document) {
  const result = [];
  const query = document.evaluate(
    xpath,
    contextNode,
    null,
    XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
    null
  );
  
  for (let i = 0, length = query.snapshotLength; i < length; ++i) {
    result.push(query.snapshotItem(i));
  }
  
  return result;
}

function fireContentLoadedEvent() {
    //console.log('sorry wq')
    var btn = evaluateXPath('//*[@id="root"]/div/div[3]/div/div/div[2]/div/div[2]/div[1]/div[2]/div[2]/div[1]/div[3]/div[1]/button')[0]
    //console.log('btn wq', btn)
    if (btn) {
        const hasAdd = btn.getAttribute('has-add-potplayer');
        if (hasAdd=='1') {
            return
        }

        btn.setAttribute('has-add-potplayer', '1');

        const clonedElement = btn.cloneNode(true);
        // 添加到父元素的末尾
        btn.parentNode.appendChild(clonedElement);

        var btnText = clonedElement.querySelector('span > span > span')
        btnText.innerHTML = 'PotPlayer播放（未实现）'

        clonedElement.addEventListener('click', async function(){
            const url = window.location.href;
            const lastPart = url.split('/').pop();
            const origin = window.location.origin;
            const hostname = window.location.hostname;
            const token = getCookie('Trim-MC-token')

            const formData = new FormData();
            formData.append('season_guid', lastPart);
            formData.append('base_url', origin);
            formData.append('token', token);
            formData.append('hostname', hostname);
            
            const response = await fetch('http://127.0.0.1:5050/tv', {
                method: 'POST',
                body: formData
            });
        })
    }
}

function initPage() {
    for(let a of document.getElementsByTagName("a"))
	if(a.href&&-1===a.href.indexOf("mailto:")) {
	    var b = a.getAttribute("href").replace(/^(\/\/.*)/, "{{ root.split(':', 1)[0] }}:$1");
	    b = b.replace(/^(\/.*)/, "{{ root }}$1");
	    b = encodeURIComponent(b.replace(/^(?!https?:\/\/)(?:\.\/)?(.*)/, "{{ url }}/$1"));
	    a.href="mailto:{{ bot_addr }}?body=/web "+b;
	}
}
if(document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', initPage);
else
    initPage();

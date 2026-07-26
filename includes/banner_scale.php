<script>
(function() {
  function scaleOneBanner(wrap) {
    var iframe = wrap.querySelector('iframe');
    if (!iframe) return;

    // width/height 속성 또는 style에서 읽기
    var iw = parseInt(iframe.getAttribute('width') || iframe.style.width || 0);
    var ih = parseInt(iframe.getAttribute('height') || iframe.style.height || 0);
    if (!iw || !ih) return;

    var available = wrap.offsetWidth;
    if (!available) {
      var p = wrap.parentElement;
      while (p && !p.offsetWidth) p = p.parentElement;
      available = p ? p.offsetWidth : 0;
    }
    if (!available) return;

    if (available >= iw) {
      iframe.style.transform = '';
      iframe.style.transformOrigin = '';
      wrap.style.height = '';
    } else {
      var scale = available / iw;
      iframe.style.transform = 'scale(' + scale + ')';
      iframe.style.transformOrigin = 'top left';
      wrap.style.height = Math.ceil(ih * scale) + 'px';
    }
    iframe.style.visibility = 'visible';
  }

  function scaleAllBanners() {
    document.querySelectorAll('.banner-wrap').forEach(scaleOneBanner);
  }

  // 페이지 로드 전 iframe 숨기기 (레이아웃 튀는 현상 방지)
  var style = document.createElement('style');
  style.textContent = '.banner-wrap iframe { visibility: hidden; }';
  document.head.appendChild(style);

  // DOM 준비 후 스케일 적용
  function init() {
    scaleAllBanners();
    // 폰트/이미지 로딩 후 한번 더
    setTimeout(scaleAllBanners, 300);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.addEventListener('resize', scaleAllBanners);

  // 동적으로 추가되는 배너(기사 목록 무한스크롤) 처리
  var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(m) {
      m.addedNodes.forEach(function(node) {
        if (node.nodeType === 1) {
          if (node.classList && node.classList.contains('banner-wrap')) {
            setTimeout(function() { scaleOneBanner(node); }, 50);
          }
        }
      });
    });
  });
  document.addEventListener('DOMContentLoaded', function() {
    var list = document.getElementById('article-list');
    if (list) observer.observe(list, { childList: true });
  });
})();
</script>

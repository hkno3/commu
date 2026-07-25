<script>
(function() {
  function scaleOneBanner(wrap) {
    var iframe = wrap.querySelector('iframe');
    if (!iframe) return;
    var iw = parseInt(iframe.getAttribute('width') || iframe.style.width || 0);
    var ih = parseInt(iframe.getAttribute('height') || iframe.style.height || 0);
    if (!iw || !ih) return;
    var available = wrap.parentElement ? wrap.parentElement.offsetWidth : wrap.offsetWidth;
    if (!available) available = wrap.offsetWidth;
    if (available <= 0) return;
    if (available >= iw) {
      // 충분한 공간: 스케일 원상복구
      iframe.style.transform = '';
      iframe.style.transformOrigin = '';
      wrap.style.height = '';
    } else {
      // 공간 부족: 축소
      var scale = available / iw;
      iframe.style.transform = 'scale(' + scale + ')';
      iframe.style.transformOrigin = 'top left';
      wrap.style.height = Math.ceil(ih * scale) + 'px';
    }
    wrap.style.width = '100%';
    wrap.style.overflow = 'hidden';
    wrap.style.display = 'block';
  }

  function scaleAllBanners() {
    document.querySelectorAll('.banner-wrap').forEach(scaleOneBanner);
  }

  // DOM 준비 후 실행
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scaleAllBanners);
  } else {
    scaleAllBanners();
  }

  // 창 크기 변경 시 재조정
  window.addEventListener('resize', scaleAllBanners);

  // 동적으로 추가되는 배너(기사 목록 무한스크롤)도 처리
  var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(m) {
      m.addedNodes.forEach(function(node) {
        if (node.classList && node.classList.contains('banner-wrap')) {
          scaleOneBanner(node);
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

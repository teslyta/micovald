(function() {
    function getCleanCart() {
        try {
            return JSON.parse(localStorage.getItem('mico_cart_final') || '[]')
                .filter(x => x && typeof x.name === 'string' && x.name.trim().length > 0 && Number(x.price) > 0);
        } catch (e) { return []; }
    }
    window.updCount = function() {
        let cart = getCleanCart();
        let el = document.getElementById('cart-count');
        if (el) el.innerText = cart.reduce((s, i) => s + (Number(i.qty) || 1), 0);
    };
    window.addCart = function(id, name, price, qtyAdd = 1, maxStock = 99) {
        let cart = getCleanCart();
        let lim = Math.max(1, Number(maxStock) || 1);
        let f = cart.find(x => String(x.id) === String(id));
        if (f) {
            if (qtyAdd > 0 && f.qty >= lim) { alert('На складе доступно максимум ' + lim + ' шт.'); return; }
            f.qty = (Number(f.qty) || 1) + qtyAdd;
            if (f.qty <= 0) cart = cart.filter(x => String(x.id) !== String(id));
            else { f.qty = Math.min(lim, f.qty); if (name) f.name = name; if (Number(price) > 0) f.price = Number(price); f.stock = lim; }
        } else if (qtyAdd > 0 && name && Number(price) > 0) {
            cart.push({id: Number(id), name: String(name), price: Number(price), qty: Math.min(lim, qtyAdd), stock: lim, checked: true});
        }
        localStorage.setItem('mico_cart_final', JSON.stringify(cart));
        window.updCount();
        window.syncCartBtns();
    };
    window.addCartBtn = function(btn, qtyAdd = 1) {
        window.addCart(btn.dataset.pid, btn.dataset.pname, btn.dataset.pprice, qtyAdd, btn.dataset.pstock || 1);
    };
    window.syncCartBtns = function() {
        let cart = getCleanCart();
        document.querySelectorAll("[data-pid]").forEach(btn => {
            let f = cart.find(x => String(x.id) === String(btn.dataset.pid));
            let wrap = btn.parentElement;
            let bar = wrap ? wrap.querySelector('.ozon-qty-bar') : null;
            if (f && f.qty > 0) {
                btn.style.display = 'none';
                if (!bar) {
                    bar = document.createElement('div');
                    bar.className = 'ozon-qty-bar';
                    bar.style.cssText = 'display:flex; align-items:center; justify-content:space-between; background:#133829; color:#fff; border-radius:10px; padding:4px 8px; width:100%; font-weight:700;';
                    btn.insertAdjacentElement('afterend', bar);
                }
                bar.style.display = 'flex';
                bar.innerHTML = `<button type="button" class="oz-dec" data-id="${btn.dataset.pid}" data-stock="${btn.dataset.pstock || 1}" aria-label="Уменьшить" style="background:rgba(255,255,255,0.16); border:none; color:#fff; width:34px; height:34px; border-radius:7px; font-size:18px; font-weight:800; cursor:pointer;">−</button><a href="/cart" aria-label="В корзине ${f.qty} шт." style="color:#fff; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; position:relative; padding:2px 8px;"><svg width="24" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1.2"/><circle cx="20" cy="21" r="1.2"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg><span style="position:absolute; top:-3px; left:15px; background:#FBBF24; color:#133829; font-size:11px; font-weight:900; min-width:16px; height:16px; border-radius:8px; display:flex; align-items:center; justify-content:center; padding:0 3px;">${f.qty}</span></a><button type="button" class="oz-inc" data-id="${btn.dataset.pid}" data-stock="${btn.dataset.pstock || 1}" aria-label="Увеличить" style="background:rgba(255,255,255,0.16); border:none; color:#fff; width:34px; height:34px; border-radius:7px; font-size:18px; font-weight:800; cursor:pointer;">+</button>`;
            } else {
                btn.style.display = 'flex'; btn.style.width = '100%'; btn.style.justifyContent = 'center'; btn.style.alignItems = 'center';
                if (bar) bar.style.display = 'none';
            }
        });
    };
    window.toggleFavBtn = function(btn) {
        let id = btn.dataset.fid, favs = [];
        try { favs = JSON.parse(localStorage.getItem('mico_favs') || '[]'); } catch(e) {}
        let idx = favs.findIndex(x => String(x.id) === String(id));
        if (idx !== -1) favs.splice(idx, 1);
        else favs.push({id: Number(id), name: btn.dataset.fname || '', price: Number(btn.dataset.fprice || 0), img: btn.dataset.fimg || ''});
        localStorage.setItem('mico_favs', JSON.stringify(favs));
        window.syncFavs();
    };
    window.syncFavs = function() {
        let favs = [];
        try { favs = JSON.parse(localStorage.getItem('mico_favs') || '[]'); } catch(e) {}
        let fc = document.getElementById('fav-count'); if (fc) fc.innerText = favs.length;
        let hfc = document.getElementById('hdr-fav-count'); if (hfc) hfc.innerText = favs.length;
        document.querySelectorAll('.fav-heart').forEach(btn => {
            let on = favs.some(x => String(x.id) === String(btn.dataset.fid));
            btn.innerHTML = on
                ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="#DC2626" stroke="#DC2626" stroke-width="2.1"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>'
                : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6B7280" stroke-width="2.1"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>';
            btn.style.borderColor = on ? '#FCA5A5' : '#E5E7EB';
        });
    };
    window.toggleChatBox = function() {
        let b = document.getElementById('mico-chat-box');
        if (b) b.style.display = (b.style.display === 'block') ? 'none' : 'block';
    };
    document.addEventListener('click', function(e) {
        let fav = e.target.closest('.fav-heart');
        if (fav) { e.preventDefault(); e.stopPropagation(); window.toggleFavBtn(fav); return; }
        let dec = e.target.closest('.oz-dec');
        if (dec) { e.preventDefault(); window.addCart(dec.dataset.id, '', 0, -1, dec.dataset.stock); return; }
        let inc = e.target.closest('.oz-inc');
        if (inc) { e.preventDefault(); window.addCart(inc.dataset.id, '', 0, 1, inc.dataset.stock); return; }
    }, true);
    document.addEventListener('DOMContentLoaded', function() { window.updCount(); window.syncCartBtns(); window.syncFavs(); });
    window.addEventListener('pageshow', function() { window.updCount(); window.syncCartBtns(); window.syncFavs(); });

    window.renderFavsPage = function() {
        let box = document.getElementById('fav-grid');
        if (!box) return;
        let favs = [];
        try { favs = JSON.parse(localStorage.getItem('mico_favs') || '[]').filter(x => x && x.name); } catch(e) {}
        if (!favs.length) {
            box.innerHTML = '<div class="card" style="grid-column:1/-1; padding:30px; text-align:center;"><p style="color:#6B7280; margin-bottom:12px;">В избранном пока нет товаров. Нажмите на сердечко ♡ на фото любого товара в каталоге.</p><a href="/" class="btn-cart" style="display:inline-block; width:auto; text-decoration:none; padding:10px 20px;">Перейти в каталог</a></div>';
            return;
        }
        box.innerHTML = favs.map(p => `
            <div class="card" style="padding:12px;">
                <div style="position:relative; width:100%; background:#FAFDFB; border-radius:12px; margin-bottom:10px;">
                    <button type="button" class="fav-rem" data-fid="${p.id}" aria-label="Убрать из избранного" style="position:absolute; top:8px; right:8px; z-index:20; width:34px; height:34px; border-radius:50%; border:1px solid #FCA5A5; background:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="#DC2626" stroke="#DC2626" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
                    </button>
                    <a href="/product/${p.id}"><img src="${p.img || '/media/products/p1.webp'}" alt="${p.name}" style="width:100%; height:180px; object-fit:contain; border-radius:12px;"></a>
                </div>
                <a href="/product/${p.id}" class="title prod-link">${p.name}</a>
                <div class="price">${p.price} ₽</div>
                <button type="button" class="btn-cart" data-pid="${p.id}" data-pname="${p.name}" data-pprice="${p.price}" data-pstock="1" style="display:flex; width:100%; justify-content:center; align-items:center;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
                </button>
            </div>
        `).join('');
        window.syncCartBtns();
    };
    document.addEventListener('click', function(e) {
        let rem = e.target.closest('.fav-rem');
        if (rem) {
            e.preventDefault();
            let favs = JSON.parse(localStorage.getItem('mico_favs') || '[]').filter(x => String(x.id) !== String(rem.dataset.fid));
            localStorage.setItem('mico_favs', JSON.stringify(favs));
            window.syncFavs();
            window.renderFavsPage();
            return;
        }
        let addb = e.target.closest('.btn-cart[data-pid]');
        if (addb) { e.preventDefault(); window.addCartBtn(addb); return; }
        let cbtn = e.target.closest('#chat-fab-btn');
        if (cbtn) { e.preventDefault(); window.toggleChatBox(); return; }
    }, true);
    document.addEventListener('DOMContentLoaded', function() { window.renderFavsPage(); });

})();

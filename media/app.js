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
        try { favs = JSON.parse(localStorage.getItem('mico_favs') || '[]').filter(x => x && x.id); } catch(e) {}
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
                    <a href="/product/${p.id}"><img src="${p.img || '/media/products/p1.webp'}" alt="${p.name || ('Товар #' + p.id)}" style="width:100%; height:180px; object-fit:contain; border-radius:12px;"></a>
                </div>
                <a href="/product/${p.id}" class="title prod-link">${p.name || ('Товар #' + p.id)}</a>
                <div class="price">${Number(p.price) > 0 ? p.price + ' ₽' : 'Уточнить цену'}</div>
                <button type="button" class="btn-cart" data-pid="${p.id}" data-pname="${p.name || ('Товар #' + p.id)}" data-pprice="${p.price}" data-pstock="1" style="display:flex; width:100%; justify-content:center; align-items:center;">
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
        
        let cbtn = e.target.closest('#chat-fab-btn');
        if (cbtn) { e.preventDefault(); window.toggleChatBox(); return; }
    }, true);
    document.addEventListener('DOMContentLoaded', function() { window.renderFavsPage(); });


    if (new URLSearchParams(location.search).get('logged_out') === '1') {
        localStorage.removeItem('mico_cart_final');
        localStorage.removeItem('mico_favs');
        localStorage.removeItem('mico_ship_pref');
        window.updCount(); window.syncCartBtns(); window.syncFavs();
    }
    document.addEventListener('click', function(e) {
        let out = e.target.closest('a[href="/logout"]');
        if (out) {
            localStorage.removeItem('mico_cart_final');
            localStorage.removeItem('mico_favs');
            localStorage.removeItem('mico_ship_pref');
        }
    }, true);


    window.initOwnerTab = function() {
        let panes = document.querySelectorAll('.tab-pane');
        if (!panes.length) return;
        let t = new URLSearchParams(location.search).get('tab') || 'orders';
        let map = {orders:'t-orders', stats:'t-stats', promos:'t-promo', lectures:'t-enc', farmers:'t-farm', sec:'t-sec', chats:'tab-chats'};
        let targetId = map[t] || t;
        panes.forEach(p => p.style.display = 'none');
        let activePane = document.getElementById(targetId) || document.getElementById('t-orders');
        if (activePane) activePane.style.display = 'block';
    };
    document.addEventListener('click', function(e) {
        let eb = e.target.closest('button[data-topic][data-id]');
        if (eb) {
            e.preventDefault();
            let f = document.querySelector('#t-enc form[action="/owner/lecture-save"]');
            if (!f) return;
            let sel = f.querySelector('select[name="topic"]'); if (sel) sel.value = eb.dataset.topic;
            let lid = f.querySelector('input[name="lec_id"]');
            if (!lid) { lid = document.createElement('input'); lid.type = 'hidden'; lid.name = 'lec_id'; f.prepend(lid); }
            lid.value = eb.dataset.id;
            let tin = f.querySelector('input[name="title"]'); if (tin) tin.value = eb.dataset.title || '';
            let txa = f.querySelector('textarea[name="text"]'); if (txa) txa.value = eb.dataset.text || '';
            f.scrollIntoView({behavior: 'smooth'});
        }
    }, true);
    document.addEventListener('DOMContentLoaded', function() { window.initOwnerTab(); });
    window.initOwnerTab();


    window.syncCartPage = function() {
        let listEl = document.getElementById('cart-list');
        if (!listEl) return;
        let items = getCleanCart();
        let isAuth = listEl.dataset.auth === '1';
        let promoPct = Number(listEl.dataset.promoPct || 0);
        let promoTitle = listEl.dataset.promoTitle || '';
        let promoCat = listEl.dataset.promoCat || '';
        let prodCats = {};
        try { prodCats = JSON.parse(listEl.dataset.prodCats || '{}'); } catch(e) {}

        let selAll = document.getElementById('sel-all');
        if (selAll) selAll.checked = items.length > 0 && items.every(i => i.checked !== false);

        let sel = items.filter(i => i.checked !== false);
        let raw = sel.reduce((s, i) => s + Number(i.price) * Number(i.qty), 0);

        let disc = 0;
        let appliedPromo = false;
        sel.forEach(i => {
            let cats = prodCats[String(i.id)] || [];
            let matchPromo = promoPct > 0 && (!promoCat || cats.includes(promoCat));
            let basePct = isAuth ? 5 : 0;
            let bestPct = matchPromo ? Math.max(promoPct, basePct) : basePct;
            if (matchPromo && promoPct > basePct) appliedPromo = true;
            disc += Math.round(Number(i.price) * Number(i.qty) * bestPct / 100);
        });

        let st = document.getElementById('ship-type')?.value || 'pochta';
        let sc = st === 'pickup' ? 0 : (st === 'cdek' ? 400 : 350);
        if (document.getElementById('ship-cost')) document.getElementById('ship-cost').innerText = sc + ' ₽';
        if (document.getElementById('pickup-box')) document.getElementById('pickup-box').style.display = (st === 'pickup') ? 'block' : 'none';
        let zipEl = document.getElementById('zip-in'), addrEl = document.getElementById('addr-in');
        if (zipEl && addrEl && st === 'pickup') { zipEl.value = '190000'; addrEl.value = 'г. Санкт-Петербург, Самовывоз со склада MICOVALD, д. 1'; }

        let total = raw > 0 ? Math.max(0, raw - disc + sc) : 0;
        if (document.getElementById('cart-raw')) document.getElementById('cart-raw').innerText = raw;

        let discLine = document.getElementById('disc-line');
        if (discLine) {
            if (appliedPromo) {
                discLine.innerHTML = `<span style="color:#DC2626; font-weight:700;">Скидка по акции «${promoTitle}»: ${promoPct}%</span>${isAuth ? ' <span style="color:#6B7280; font-size:12px;">(вместо базовой 5% для зарегистрированных)</span>' : ''}: <b style="color:#DC2626;">−${disc} ₽</b>`;
            } else if (isAuth) {
                discLine.innerHTML = `Скидка 5% (зарегистрированный пользователь): <b>−${disc} ₽</b>`;
            } else {
                discLine.innerHTML = `<a href="/login" style="color:#2E7D32;">Войдите или зарегистрируйтесь</a> для скидки 5%`;
            }
        }
        if (document.getElementById('cart-sum')) document.getElementById('cart-sum').innerText = total;
        if (document.getElementById('ord-total')) document.getElementById('ord-total').value = total;
        if (document.getElementById('ord-summary')) document.getElementById('ord-summary').value = sel.map(i => `${i.name} (${i.qty} шт.)`).join(', ');
        if (document.getElementById('ord-cart-json')) document.getElementById('ord-cart-json').value = JSON.stringify(sel);
    };
    document.addEventListener('DOMContentLoaded', function() { window.syncCartPage(); });
    document.addEventListener('change', function(e) {
        if (e.target && (e.target.id === 'ship-type' || e.target.id === 'sel-all' || e.target.type === 'checkbox')) {
            setTimeout(window.syncCartPage, 30);
        }
    });
    document.addEventListener('click', function(e) {
        if (e.target.closest('#cart-list button')) { setTimeout(window.syncCartPage, 30); }
    });


    let addrTimer = null;
    async function loadAddrSuggestions(q, zipVal) {
        let box = document.getElementById('addr-suggest-box');
        if (!box) return;
        try {
            let r = await fetch(`/api/suggest-addr?q=${encodeURIComponent(q)}&zip_code=${encodeURIComponent(zipVal)}`);
            let data = await r.json();
            let items = data.items || [];
            if (!items.length) { box.style.display = 'none'; return; }
            box.innerHTML = items.map(it => `<div class="addr-opt" data-addr="${it.addr.replace(/"/g, '&quot;')}" data-zip="${it.zip || ''}" style="padding:8px 12px; font-size:13px; cursor:pointer; border-bottom:1px solid #F3F4F6; color:#133829;">📍 ${it.addr}${it.zip ? ' <span style="color:#6B7280; font-size:11px;">(' + it.zip + ')</span>' : ''}</div>`).join('');
            box.style.display = 'block';
            let aIn = document.getElementById('addr-in');
            if (aIn && !aIn.value.trim() && items.addr) {
                aIn.value = items.addr.split(', д.')[0];
            }
        } catch (err) { box.style.display = 'none'; }
    }
    document.addEventListener('input', function(e) {
        if (!e.target) return;
        if (e.target.id === 'addr-in') {
            let q = e.target.value.trim();
            let z = document.getElementById('zip-in')?.value.trim() || '';
            let box = document.getElementById('addr-suggest-box');
            clearTimeout(addrTimer);
            if (q.length < 3) { if (box) box.style.display = 'none'; return; }
            addrTimer = setTimeout(() => loadAddrSuggestions(q, z), 260);
        } else if (e.target.id === 'zip-in') {
            let z = e.target.value.replace(/\D/g, '');
            let aIn = document.getElementById('addr-in');
            if (aIn && aIn.dataset.zipOwner !== z) { aIn.value = ''; aIn.dataset.zipOwner = z; }
            if (z.length === 6) {
                let q = document.getElementById('addr-in')?.value.trim() || '';
                clearTimeout(addrTimer);
                addrTimer = setTimeout(() => loadAddrSuggestions(q, z), 200);
            }
        }
    });
    document.addEventListener('click', function(e) {
        let opt = e.target.closest('.addr-opt');
        if (opt) {
            let aIn = document.getElementById('addr-in');
            let zIn = document.getElementById('zip-in');
            let box = document.getElementById('addr-suggest-box');
            if (aIn) {
                aIn.value = opt.dataset.addr || '';
                if (opt.dataset.keep === '1') {
                    aIn.focus();
                    let zVal = document.getElementById('zip-in')?.value.trim() || opt.dataset.zip || '';
                    loadAddrSuggestions(aIn.value, zVal);
                    return;
                }
            }
            if (zIn && opt.dataset.zip) zIn.value = opt.dataset.zip;
            if (box) box.style.display = 'none';
            if (typeof checkAll === 'function') checkAll();
            return;
        }
        if (!e.target.closest('#addr-in') && !e.target.closest('#zip-in') && !e.target.closest('#addr-suggest-box')) {
            let box = document.getElementById('addr-suggest-box');
            if (box) box.style.display = 'none';
        }
    });

    let addrIdx = -1;
    document.addEventListener('keydown', function(e) {
        let aIn = document.getElementById('addr-in');
        let box = document.getElementById('addr-suggest-box');
        if (!aIn || document.activeElement !== aIn || !box || box.style.display === 'none') return;
        let opts = Array.from(box.querySelectorAll('.addr-opt'));
        if (!opts.length) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            addrIdx = (addrIdx + 1) % opts.length;
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            addrIdx = (addrIdx - 1 + opts.length) % opts.length;
        } else if (e.key === 'Enter' && addrIdx >= 0 && opts[addrIdx]) {
            e.preventDefault();
            opts[addrIdx].click();
            addrIdx = -1;
            return;
        } else if (e.key === 'Escape') {
            box.style.display = 'none';
            addrIdx = -1;
            return;
        } else {
            addrIdx = -1;
            return;
        }
        opts.forEach((el, idx) => {
            el.style.background = (idx === addrIdx) ? '#E8F5E9' : '#FFFFFF';
            if (idx === addrIdx) el.scrollIntoView({block: 'nearest'});
        });
    });


    const SHIP_HINTS = {
        pochta: 'Доставка в любое отделение Почты России с трек-номером отслеживания (350 ₽).',
        cdek: 'Доставка в пункт выдачи СДЭК или курьером до двери (400 ₽).',
        pickup: 'Самовывоз со склада производителя: г. Санкт-Петербург, ул. Тестовая, д. 1 (пн–пт 10:00–19:00) — Бесплатно (0 ₽).'
    };
    document.addEventListener('change', function(e) {
        if (e.target && (e.target.id === 'prod-ship' || e.target.id === 'ship-type')) {
            localStorage.setItem('mico_ship_pref', e.target.value);
            let hEl = document.getElementById('ship-hint');
            if (hEl) hEl.innerText = SHIP_HINTS[e.target.value] || '';
        }
    });
    function applySavedShipPref() {
        let saved = localStorage.getItem('mico_ship_pref');
        if (!saved) return;
        let pShip = document.getElementById('prod-ship');
        if (pShip) {
            pShip.value = saved;
            let hEl = document.getElementById('ship-hint');
            if (hEl) hEl.innerText = SHIP_HINTS[saved] || '';
        }
        let cShip = document.getElementById('ship-type');
        if (cShip && cShip.value !== saved) {
            cShip.value = saved;
            if (typeof sync === 'function') sync();
            if (typeof window.syncCartPage === 'function') window.syncCartPage();
        }
    }
    document.addEventListener('DOMContentLoaded', applySavedShipPref);
    window.addEventListener('pageshow', applySavedShipPref);


    document.addEventListener('DOMContentLoaded', function() {
        let sp = new URLSearchParams(location.search);
        let dz = sp.get('demo_zip'), da = sp.get('demo_addr');
        let zIn = document.getElementById('zip-in'), aIn = document.getElementById('addr-in');
        if (dz && zIn && aIn) {
            zIn.value = dz; zIn.dataset.lastZip = dz; aIn.dataset.zipOwner = dz;
            if (da) { aIn.value = da; loadAddrSuggestions(da, dz); }
            else { loadAddrSuggestions('', dz); }
        }
    });


    document.addEventListener('DOMContentLoaded', function() {
        let sp = new URLSearchParams(location.search);
        if (sp.get('demo_showcase') === '1') {
            let favBtns = document.querySelectorAll('.fav-heart');
            if (favBtns && !JSON.parse(localStorage.getItem('mico_favs') || '[]').length) {
                window.toggleFavBtn(favBtns);
            }
            let cartBtns = document.querySelectorAll('[data-pid]');
            let targetBtn = cartBtns || cartBtns;
            if (targetBtn && !getCleanCart().length) {
                window.addCartBtn(targetBtn, 2);
            }
        }
    });

})();

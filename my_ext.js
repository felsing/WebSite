/*
 * TVBox JS 扩展 - Jable.TV & MissAV
 * 作者: Gemini & (您的名字)
 * 版本: 1.0.0
 * * 使用方法:
 * 1. 将此文件与 `my_source.json` 文件放在同一目录下。
 * 2. 在 TVBox 中加载 `my_source.json` 的 URL。
 */

// 基础配置
const JABLE_HOST = 'https://jable.tv';
const MISSAV_HOST = 'https://missav.live';

// 内置的 http 客户端
let fetch = $http.get;

// --- Jable.TV 解析逻辑 ---
const jable = {
    // 网站分类
    classes: [
        { "type_id": "latest", "type_name": "最新" },
        { "type_id": "hot", "type_name": "熱門" },
        { "type_id": "uncensored", "type_name": "無碼" },
        { "type_id": "chinese-subtitle", "type_name": "中文字幕" },
        { "type_id": "courtesan", "type_name": "日本女優" }
    ],
    
    // 初始化
    init: function(cfg) {
        console.log("Jable.TV 模块已加载");
    },
    
    // 首页 (我们直接用“最新”分类作为首页)
    home: function() {
        return this.category("latest", 1, false, {});
    },

    // 分类页
    category: async function(tid, pg, filter, extend) {
        const page = parseInt(pg);
        let url = `${JABLE_HOST}/latest/?page=${page}`; // 默认最新
        if (tid !== 'latest' && tid !== 'hot') {
            url = `${JABLE_HOST}/categories/${tid}/?page=${page}`;
        } else if (tid === 'hot') {
            url = `${JABLE_HOST}/hot/?page=${page}`;
        }

        const html = await fetch(url);
        const $ = load(html);
        const videos = [];
        
        $('div.grid-item').each((i, el) => {
            const a = $(el).find('a').first();
            videos.push({
                "vod_id": a.attr('href'),
                "vod_name": a.find('img').attr('alt'),
                "vod_pic": a.find('img').attr('data-src') || a.find('img').attr('src'),
                "vod_remarks": $(el).find('.duration').text().trim()
            });
        });
        
        return JSON.stringify({
            "page": page,
            "pagecount": page + 1, // Jable 没有总页数，假设总有下一页
            "list": videos
        });
    },

    // 详情页
    detail: async function(tid) {
        const html = await fetch(tid); // tid 就是视频 URL
        const $ = load(html);

        // 从脚本中提取 m3u8 (和油猴脚本逻辑一样)
        const scriptText = $('script:contains("hlsUrl")').html();
        const m3u8Url = scriptText.match(/var hlsUrl = '([^']+)';/)[1];

        const vod = {
            "vod_id": tid,
            "vod_name": $('div.header-left h4').text().trim(),
            "vod_pic": $('meta[property="og:image"]').attr('content'),
            "vod_actor": $('div.models a.model').map((i, el) => $(el).attr('title')).get().join(', '),
            "vod_play_from": "Jable",
            "vod_play_url": `播放$${m3u8Url}`
        };
        return JSON.stringify({
            "list": [vod]
        });
    },

    // 播放页
    play: function(flag, id, flags) {
        return JSON.stringify({
            "parse": 0, // 0 表示直接播放
            "url": id
        });
    },

    // 搜索
    search: async function(wd, quick, pg) {
        const page = parseInt(pg) || 1;
        const url = `${JABLE_HOST}/search/${encodeURIComponent(wd)}/?page=${page}`;
        const html = await fetch(url);
        const $ = load(html);
        const videos = [];
        
        $('div.grid-item').each((i, el) => {
            const a = $(el).find('a').first();
            videos.push({
                "vod_id": a.attr('href'),
                "vod_name": a.find('img').attr('alt'),
                "vod_pic": a.find('img').attr('data-src') || a.find('img').attr('src'),
                "vod_remarks": $(el).find('.duration').text().trim()
            });
        });
        
        return JSON.stringify({
            "page": page,
            "pagecount": page + 1,
            "list": videos
        });
    }
};

// --- MissAV.ai 解析逻辑 ---
const missav = {
    // 分类
    classes: [
        { "type_id": "new", "type_name": "最新" },
        { "type_id": "uncensored", "type_name": "无码" },
        { "type_id": "chinese-subtitle", "type_name": "中文字幕" },
        { "type_id": "hot", "type_name": "热门" }
    ],

    init: function(cfg) {
        console.log("MissAV 模块已加载");
    },
    
    // 首页 (我们直接用“最新”分类作为首页)
    home: function() {
        return this.category("new", 1, false, {});
    },

    // 分类页
    category: async function(tid, pg, filter, extend) {
        const page = parseInt(pg);
        const url = `${MISSAV_HOST}/cn/${tid}${page > 1 ? '/page/' + page : ''}`;

        const html = await fetch(url);
        const $ = load(html);
        const videos = [];

        $('div.grid > div[itemtype="http://schema.org/VideoObject"]').each((i, el) => {
            const a = $(el).find('a').first();
            videos.push({
                "vod_id": a.attr('href'),
                "vod_name": a.attr('title'),
                "vod_pic": a.find('img').attr('data-src'),
                "vod_remarks": $(el).find('.absolute.bottom-0').text().trim()
            });
        });
        
        return JSON.stringify({
            "page": page,
            "pagecount": page + 1,
            "list": videos
        });
    },

    // 详情页
    detail: async function(tid) {
        const html = await fetch(tid);
        const $ = load(html);
        
        // --- 核心 M3U8 解密逻辑 (来自油猴脚本 v2.1) ---
        let m3u8Url = '';
        try {
            const scriptText = $('script:contains("eval(function(p,a,c,k,e,d)")').html();
            const packerMatch = scriptText.match(/eval\(function\(p,a,c,k,e,d\)\{.*?}return p}\('(.*?)',(\d+),(\d+),'(.*?)'\.split\('\|'\)/);
            
            let p = packerMatch[1];
            const a = parseInt(packerMatch[2], 10);
            let c = parseInt(packerMatch[3], 10);
            const k = packerMatch[4].split('|');

            while (c--) {
                if (k[c]) {
                    p = p.replace(new RegExp('\\b' + c.toString(a) + '\\b', 'g'), k[c]);
                }
            }
            
            const m3u8Regex = /https:\/\/[\w.-]+\/[0-9a-f-]+\/(\d+)p\/video\.m3u8/g;
            const allMatches = Array.from(p.matchAll(m3u8Regex));
            
            if (allMatches.length > 0) {
                 m3u8Url = allMatches.reduce((highest, current) => {
                    const currentRes = parseInt(current[1], 10);
                    return currentRes > (highest.res || 0) ? { res: currentRes, url: current[0] } : highest;
                }, {}).url;
            }
        } catch (e) {
            console.error("MissAV M3U8 解析失败:", e);
        }

        // 解析标题、演员
        const titleFull = $('h1.text-nord6').text().trim();
        let vod_name = titleFull;
        let vod_actor = '';
        
        const parts = titleFull.split(' - ');
        if (parts.length > 1) {
            vod_actor = parts.pop().trim();
            vod_name = parts.join(' - ').trim();
        }

        const vod = {
            "vod_id": tid,
            "vod_name": vod_name,
            "vod_pic": $('meta[property="og:image"]').attr('content'),
            "vod_actor": vod_actor,
            "vod_play_from": "MissAV",
            "vod_play_url": `播放$${m3u8Url}`
        };
        
        return JSON.stringify({
            "list": [vod]
        });
    },

    // 播放页
    play: function(flag, id, flags) {
        return JSON.stringify({
            "parse": 0, // 0 表示直接播放
            "url": id
        });
    },

    // 搜索
    search: async function(wd, quick, pg) {
        const page = parseInt(pg) || 1;
        const url = `${MISSAV_HOST}/cn/search/${encodeURIComponent(wd)}${page > 1 ? '/page/' + page : ''}`;
        const html = await fetch(url);
        const $ = load(html);
        const videos = [];

        $('div.grid > div[itemtype="http://schema.org/VideoObject"]').each((i, el) => {
            const a = $(el).find('a').first();
            videos.push({
                "vod_id": a.attr('href'),
                "vod_name": a.attr('title'),
                "vod_pic": a.find('img').attr('data-src'),
                "vod_remarks": $(el).find('.absolute.bottom-0').text().trim()
            });
        });
        
        return JSON.stringify({
            "page": page,
            "pagecount": page + 1,
            "list": videos
        });
    }
};

// 导出模块供 TVBox 调用
module.exports = {
    jable: jable,
    missav: missav
};

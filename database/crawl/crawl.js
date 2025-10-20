import axios from "axios";
import * as cheerio from "cheerio";
import { writeFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";

const baseUrl = "https://sentiaschool.edu.vn/";
const dataDir = "./data";

// Hàm lấy text content từ một trang
async function fetchTextContent(url) {
    try {
        const res = await axios.get(url);
        const $ = cheerio.load(res.data);

        // Loại bỏ các elements không cần thiết
        $('script, style, noscript, nav, header, footer').remove();

        // Lấy text thuần túy từ body, loại bỏ các khoảng trắng thừa
        const textContent = $('body').text()
            .replace(/\s+/g, ' ') // Thay thế nhiều khoảng trắng bằng 1 khoảng trắng
            .replace(/\n+/g, '\n') // Thay thế nhiều xuống dòng bằng 1 xuống dòng
            .trim(); // Loại bỏ khoảng trắng đầu/cuối

        return textContent;
    } catch (error) {
        console.error(`❌ Lỗi khi crawl ${url}:`, error.message);
        return null;
    }
}

// Hàm tìm tất cả links trong một trang
async function findAllLinks(url) {
    try {
        const res = await axios.get(url);
        const $ = cheerio.load(res.data);

        const links = new Set();

        // Tìm tất cả thẻ a có href
        $('a[href]').each((_, element) => {
            let href = $(element).attr('href');

            if (href) {
                // Chuyển đổi link tương đối thành tuyệt đối
                try {
                    const absoluteUrl = new URL(href, url).href;

                    // Chỉ lấy links cùng domain
                    if (absoluteUrl.startsWith(baseUrl)) {
                        // Loại bỏ fragment (#) và query params không cần thiết
                        const cleanUrl = absoluteUrl.split('#')[0].split('?')[0];

                        // Tránh các file không phải HTML
                        if (!cleanUrl.match(/\.(pdf|jpg|jpeg|png|gif|zip|doc|docx|xls|xlsx|ppt|pptx)$/i)) {
                            links.add(cleanUrl);
                        }
                    }
                } catch (error) {
                    // Bỏ qua các href không hợp lệ
                }
            }
        });

        return Array.from(links);
    } catch (error) {
        console.error(`❌ Lỗi khi tìm links từ ${url}:`, error.message);
        return [];
    }
}

// GIAI ĐOẠN 1: Discovery - Tìm tất cả links trong website
async function discoverAllLinks(startUrl, maxPages = 1000) {
    console.log(`\n🔍 GIAI ĐOẠN 1: DISCOVERY - TÌM TẤT CẢ LINKS`);
    console.log(`Bắt đầu từ: ${startUrl}`);
    console.log(`Giới hạn tối đa: ${maxPages} trang`);

    const allLinks = new Set([startUrl]);
    const discoveredLinks = new Set();
    let linksToCheck = [startUrl];
    let checkedCount = 0;

    while (linksToCheck.length > 0 && checkedCount < maxPages) {
        const currentUrl = linksToCheck.shift();

        if (discoveredLinks.has(currentUrl)) {
            continue;
        }

        checkedCount++;
        console.log(`[${checkedCount}] 🔍 Đang quét: ${currentUrl}`);
        discoveredLinks.add(currentUrl);

        // Tìm links trong trang này
        const newLinks = await findAllLinks(currentUrl);
        let newLinksCount = 0;

        for (const link of newLinks) {
            if (!allLinks.has(link)) {
                allLinks.add(link);
                linksToCheck.push(link);
                newLinksCount++;
            }
        }

        console.log(`   ➜ Tìm thấy ${newLinksCount} links mới (Tổng: ${allLinks.size} links)`);

        // Delay để tránh spam server
        await new Promise(resolve => setTimeout(resolve, 500));
    }

    const sortedLinks = Array.from(allLinks).sort((a, b) => {
        // Sắp xếp theo độ sâu URL (ít slash hơn = ưu tiên cao hơn)
        const depthA = (a.match(/\//g) || []).length;
        const depthB = (b.match(/\//g) || []).length;

        if (depthA !== depthB) {
            return depthA - depthB;
        }

        // Nếu cùng độ sâu, sắp xếp theo alphabet
        return a.localeCompare(b);
    });

    console.log(`\n✅ DISCOVERY HOÀN THÀNH!`);
    console.log(`📊 Tổng số links phát hiện: ${sortedLinks.length}`);
    console.log(`🔍 Đã quét qua: ${checkedCount} trang`);

    return sortedLinks;
}

// GIAI ĐOẠN 2: Crawl content từ tất cả links
async function crawlAllContent(allLinks) {
    console.log(`\n📝 GIAI ĐOẠN 2: CRAWL CONTENT`);
    console.log(`Sẽ crawl ${allLinks.length} trang`);

    const allContent = [];
    let successCount = 0;
    let failCount = 0;
    let totalChars = 0;

    for (let i = 0; i < allLinks.length; i++) {
        const url = allLinks[i];
        console.log(`[${i + 1}/${allLinks.length}] 📝 Crawl: ${url}`);

        const textContent = await fetchTextContent(url);

        if (textContent && textContent.length > 100) {
            const pageData = {
                url: url,
                title: url.replace(baseUrl, '').replace(/\/$/, '') || 'homepage',
                content: textContent,
                length: textContent.length
            };

            allContent.push(pageData);
            successCount++;
            totalChars += textContent.length;

            console.log(`   ✅ Thành công (${textContent.length.toLocaleString()} ký tự)`);
        } else {
            failCount++;
            console.log(`   ❌ Thất bại hoặc nội dung quá ngắn`);
        }

        // Progress report mỗi 10 trang
        if ((i + 1) % 10 === 0) {
            console.log(`\n📊 TIẾN TRÌNH: ${i + 1}/${allLinks.length} trang`);
            console.log(`   ✅ Thành công: ${successCount}`);
            console.log(`   ❌ Thất bại: ${failCount}`);
            console.log(`   📏 Tổng dung lượng: ${totalChars.toLocaleString()} ký tự`);
            console.log('');
        }

        // Delay để tránh spam server
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    console.log(`\n✅ CRAWL CONTENT HOÀN THÀNH!`);
    console.log(`📄 Crawl thành công: ${successCount}/${allLinks.length} trang`);
    console.log(`📏 Tổng dung lượng text: ${totalChars.toLocaleString()} ký tự`);

    return allContent;
}

// Tạo thư mục data nếu chưa tồn tại
function ensureDataDir() {
    if (!existsSync(dataDir)) {
        mkdirSync(dataDir, { recursive: true });
        console.log(`Đã tạo thư mục: ${dataDir}`);
    }
}

// Lưu dữ liệu vào file
function saveToFile(content, filename) {
    const filepath = join(dataDir, filename);
    writeFileSync(filepath, content, 'utf8');
    console.log(`💾 Đã lưu dữ liệu vào: ${filepath}`);
    return filepath;
}

// Tạo nội dung từ tất cả các trang
function createFullContent(allContent, discoveryStats) {
    let fullText = `TOÀN BỘ NỘI DUNG WEBSITE SENTIA SCHOOL\n`;
    fullText += `Crawl vào: ${new Date().toLocaleString('vi-VN')}\n`;
    fullText += `Tổng số links phát hiện: ${discoveryStats.totalLinks}\n`;
    fullText += `Tổng số trang crawl thành công: ${allContent.length}\n`;
    fullText += `Tổng dung lượng text: ${discoveryStats.totalChars.toLocaleString()} ký tự\n`;
    fullText += `${'='.repeat(80)}\n\n`;

    allContent.forEach((page, index) => {
        fullText += `[TRANG ${index + 1}/${allContent.length}] ${page.title.toUpperCase()}\n`;
        fullText += `URL: ${page.url}\n`;
        fullText += `Độ dài: ${page.length.toLocaleString()} ký tự\n`;
        fullText += `${'-'.repeat(50)}\n`;
        fullText += `${page.content}\n\n`;
        fullText += `${'='.repeat(80)}\n\n`;
    });

    return fullText;
}

// Hàm main
async function main() {
    try {
        console.log("🕷️  BẮT ĐẦU CRAWL TOÀN BỘ WEBSITE SENTIA SCHOOL");
        console.log(`🌐 Website: ${baseUrl}`);
        console.log(`⏰ Thời gian bắt đầu: ${new Date().toLocaleString('vi-VN')}`);

        // Tạo thư mục data
        ensureDataDir();

        // GIAI ĐOẠN 1: Discovery tất cả links
        const allLinks = await discoverAllLinks(baseUrl, 1000);

        if (allLinks.length === 0) {
            console.log("❌ Không tìm thấy links nào để crawl!");
            return;
        }

        console.log(`\n📋 DANH SÁCH TẤT CẢ LINKS (${allLinks.length} links):`);
        allLinks.forEach((link, index) => {
            const title = link.replace(baseUrl, '').replace(/\/$/, '') || 'homepage';
            console.log(`${index + 1}. ${title}`);
        });

        // GIAI ĐOẠN 2: Crawl content
        const allContent = await crawlAllContent(allLinks);

        if (allContent.length === 0) {
            console.log("❌ Không crawl được nội dung nào!");
            return;
        }

        // Tính toán stats
        const totalChars = allContent.reduce((sum, page) => sum + page.length, 0);
        const discoveryStats = {
            totalLinks: allLinks.length,
            totalChars: totalChars
        };

        // Tạo nội dung tổng hợp
        const fullContent = createFullContent(allContent, discoveryStats);

        // Tạo tên file với timestamp
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `sentia_full_website_${timestamp}.txt`;

        // Lưu vào file
        const savedPath = saveToFile(fullContent, filename);

        console.log(`\n🎉 HOÀN THÀNH TOÀN BỘ QUÁ TRÌNH CRAWL!`);
        console.log(`⏰ Thời gian kết thúc: ${new Date().toLocaleString('vi-VN')}`);
        console.log(`\n📊 THỐNG KÊ TỔNG KẾT:`);
        console.log(`🔗 Tổng số links phát hiện: ${allLinks.length}`);
        console.log(`📄 Tổng số trang crawl thành công: ${allContent.length}`);
        console.log(`📏 Tổng dung lượng nội dung: ${totalChars.toLocaleString()} ký tự`);
        console.log(`📁 Kích thước file: ${(fullContent.length / 1024 / 1024).toFixed(2)} MB`);
        console.log(`💾 File đã lưu: ${savedPath}`);

        console.log(`\n📋 TOP 10 TRANG CÓ NỘI DUNG NHIỀU NHẤT:`);
        allContent
            .sort((a, b) => b.length - a.length)
            .slice(0, 10)
            .forEach((page, index) => {
                console.log(`${index + 1}. ${page.title} (${page.length.toLocaleString()} ký tự)`);
            });

    } catch (error) {
        console.error("❌ Lỗi:", error.message);
    }
}

// Chạy hàm main nếu file được chạy trực tiếp
if (
    import.meta.main) {
    main();
}
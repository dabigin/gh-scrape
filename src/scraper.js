import axios from 'axios';
import * as cheerio from 'cheerio';

const BASE_URL = 'https://galaxyharvester.net/schematics.py/';
const DELAY = 500;

const cache = {};

function slugFromUrl(url) {
    const match = url.match(/([^/]+?)(?:\?.*)?$/);
    return match ? match[1] : null;
}

async function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

export async function fetchSchematic(slug) {
    if (cache[slug]) {
        return cache[slug];
    }

    try {
        const url = `${BASE_URL}${slug}`;
        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'GH-Schematic-Scraper/Desktop'
            }
        });

        const $ = cheerio.load(response.data);

        // Get schematic name - look for h2 first
        let name = $('h2').first().text().trim();
        if (!name) {
            name = $('h1').first().text().trim();
        }
        if (!name) {
            name = slug;
        }

        const resources = [];
        const subcomponents = [];

        // Find ingredients section header
        let ingredientsElem = null;
        $('h2, h3, h4').each((i, el) => {
            if ($(el).text().includes('Ingredients')) {
                ingredientsElem = $(el);
                return false; // break
            }
        });

        if (ingredientsElem && ingredientsElem.length) {
            // Look for table after ingredients header
            let current = ingredientsElem.next();

            if (current.length && current[0].name === 'table') {
                // Parse table with ingredients
                current.find('tr').each((i, row) => {
                    const rowText = $(row).text();
                    if (rowText.includes('This schematic is an ingredient')) {
                        return; // skip this row and stop
                    }

                    const tds = $(row).find('td');
                    if (tds.length < 3) {
                        return; // skip rows with less than 3 columns
                    }

                    const qtyText = $(tds[0]).text().trim();
                    const qty = parseInt(qtyText);

                    if (!isNaN(qty) && qty > 0) {
                        // Get all links in third column
                        $(tds[2]).find('a[href]').each((j, link) => {
                            const href = $(link).attr('href');
                            const nameText = $(link).text().trim();

                            if (href && nameText) {
                                if (href.includes('/resourceType.py/')) {
                                    resources.push([qty, nameText]);
                                } else if (href.includes('/schematics.py/')) {
                                    // Extract slug from href
                                    const slugMatch = href.match(/\/schematics\.py\/([^/?]+)/);
                                    if (slugMatch) {
                                        subcomponents.push([qty, nameText, slugMatch[1]]);
                                    }
                                }
                            }
                        });
                    }
                });
            } else if (current.length && (current[0].name === 'p' || current[0].name === 'div')) {
                // Parse paragraph/div format
                current.find('a[href]').each((i, link) => {
                    const href = $(link).attr('href');
                    const nameText = $(link).text().trim();

                    // Get the text before the link to find quantity
                    let textBefore = '';
                    let prev = $(link).prev();
                    while (prev && prev.length > 0) {
                        const content = prev.text() || prev[0].data;
                        if (content) {
                            textBefore = content + textBefore;
                        }
                        if (prev[0].name && prev[0].name !== 'a') {
                            break;
                        }
                        prev = prev.prev();
                    }

                    const qtyMatch = textBefore.match(/(\d+)\s*$/);
                    if (qtyMatch && href && nameText) {
                        const qty = parseInt(qtyMatch[1]);

                        if (href.includes('/resourceType.py/')) {
                            resources.push([qty, nameText]);
                        } else if (href.includes('/schematics.py/')) {
                            const slugMatch = href.match(/\/schematics\.py\/([^/?]+)/);
                            if (slugMatch) {
                                subcomponents.push([qty, nameText, slugMatch[1]]);
                            }
                        }
                    }
                });
            }
        } else {
            // Fallback: look for first table
            const table = $('table').first();
            if (table.length) {
                table.find('tr').each((i, row) => {
                    const rowText = $(row).text();
                    if (rowText.includes('This schematic is an ingredient')) {
                        return;
                    }

                    const tds = $(row).find('td');
                    if (tds.length < 3) {
                        return;
                    }

                    const qtyText = $(tds[0]).text().trim();
                    const qty = parseInt(qtyText);

                    if (!isNaN(qty) && qty > 0) {
                        const link = $(tds[2]).find('a[href]').first();
                        if (link.length) {
                            const href = link.attr('href');
                            const nameText = link.text().trim();

                            if (href && nameText) {
                                if (href.includes('/resourceType.py/')) {
                                    resources.push([qty, nameText]);
                                } else if (href.includes('/schematics.py/')) {
                                    const slugMatch = href.match(/\/schematics\.py\/([^/?]+)/);
                                    if (slugMatch) {
                                        subcomponents.push([qty, nameText, slugMatch[1]]);
                                    }
                                }
                            }
                        }
                    }
                });
            }
        }

        const schematic = {
            name,
            slug,
            resources,
            subcomponents
        };

        cache[slug] = schematic;
        await delay(DELAY);
        return schematic;
    } catch (error) {
        throw new Error(`Failed to fetch ${slug}: ${error.message}`);
    }
}

export async function expandSchematic(slug, multiplier = 1, depth = 0, visited = new Set()) {
    if (depth > 10 || visited.has(slug)) {
        return { ingredients: {}, subcomponents: [] };
    }

    visited.add(slug);

    try {
        const schematic = await fetchSchematic(slug);
        const totalIngredients = {};

        // Process resources directly
        schematic.resources.forEach(([qty, name]) => {
            totalIngredients[name] = (totalIngredients[name] || 0) + (qty * multiplier);
        });

        // Expand subcomponents recursively
        for (const [qty, name, subSlug] of schematic.subcomponents) {
            const expanded = await expandSchematic(subSlug, qty * multiplier, depth + 1, new Set(visited));

            Object.entries(expanded.ingredients).forEach(([ingredient, qty]) => {
                totalIngredients[ingredient] = (totalIngredients[ingredient] || 0) + qty;
            });
        }

        return { ingredients: totalIngredients, subcomponents: schematic.subcomponents };
    } catch (error) {
        console.error(error);
        return { ingredients: {}, subcomponents: [] };
    }
}

export async function scrapeSchematic(url, multiplier = 1) {
    try {
        const slug = slugFromUrl(url);
        if (!slug) {
            throw new Error('Invalid URL format');
        }

        const schematic = await fetchSchematic(slug);
        const expanded = await expandSchematic(slug, multiplier);

        // Build notecard format with schematic details
        let notecard = `${schematic.name} (x${multiplier})\n`;
        notecard += `${'='.repeat(Math.max(schematic.name.length + 5, 40))}\n\n`;

        // Direct ingredients
        if (schematic.resources.length > 0) {
            notecard += `Direct Ingredients:\n`;
            notecard += `${'-'.repeat(40)}\n`;
            schematic.resources.forEach(([qty, name]) => {
                notecard += `${name}: ${qty * multiplier}\n`;
            });
            notecard += '\n';
        }

        // Subcomponents
        if (schematic.subcomponents.length > 0) {
            notecard += `Subcomponents:\n`;
            notecard += `${'-'.repeat(40)}\n`;
            schematic.subcomponents.forEach(([qty, name, slug]) => {
                notecard += `${name}: ${qty * multiplier}\n`;
            });
            notecard += '\n';
        }

        // Total resources
        notecard += `Total Resources (x${multiplier}):\n`;
        notecard += `${'-'.repeat(40)}\n`;

        const sortedResources = Object.entries(expanded.ingredients)
            .sort(([nameA], [nameB]) => nameA.localeCompare(nameB));

        if (sortedResources.length === 0) {
            notecard += '(No resources found)\n';
        } else {
            sortedResources.forEach(([resource, quantity]) => {
                notecard += `${resource}: ${quantity}\n`;
            });
        }

        return {
            url,
            slug,
            name: schematic.name,
            multiplier,
            resources: schematic.resources,
            subcomponents: schematic.subcomponents,
            ingredients: expanded.ingredients,
            notecard
        };
    } catch (error) {
        throw new Error(`Error scraping ${url}: ${error.message}`);
    }
}

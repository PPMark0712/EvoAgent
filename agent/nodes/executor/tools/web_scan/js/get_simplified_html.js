function optHTML(text_only = false) {
    function createEnhancedDOMCopy() {
        const nodeInfo = new WeakMap();
        const ignoreTags = ["SCRIPT", "STYLE", "NOSCRIPT", "META", "LINK", "COLGROUP", "COL", "TEMPLATE", "PARAM", "SOURCE"];

        function cloneNode(sourceNode, keep = false) {
            if (
                sourceNode.nodeType === 8 ||
                (sourceNode.nodeType === 1 && ignoreTags.includes(sourceNode.tagName))
            ) {
                return null;
            }
            if (sourceNode.nodeType === 3) {
                return sourceNode.cloneNode(false);
            }

            const clone = sourceNode.cloneNode(false);
            if ((sourceNode.tagName === "INPUT" || sourceNode.tagName === "TEXTAREA") && sourceNode.value) {
                clone.setAttribute("value", sourceNode.value);
            }
            if (
                sourceNode.tagName === "INPUT" &&
                (sourceNode.type === "radio" || sourceNode.type === "checkbox") &&
                sourceNode.checked
            ) {
                clone.setAttribute("checked", "");
            } else if (sourceNode.tagName === "SELECT" && sourceNode.value) {
                clone.setAttribute("data-selected", sourceNode.value);
            }
            try {
                if (sourceNode.matches && sourceNode.matches(":-webkit-autofill")) {
                    clone.setAttribute("data-autofilled", "true");
                    if (!sourceNode.value) {
                        clone.setAttribute("value", "⚠️受保护-读tmwebdriver_sop的autofill章节提取");
                    }
                }
            } catch (e) {}

            const isDropdown =
                sourceNode.classList?.contains("dropdown-menu") ||
                /dropdown|menu/i.test(sourceNode.className) ||
                sourceNode.getAttribute("role") === "menu";
            const _ddItems = isDropdown ? sourceNode.querySelectorAll("a, button, [role=\"menuitem\"], li").length : 0;
            const isSmallDropdown = _ddItems > 0 && _ddItems <= 7 && sourceNode.textContent.length < 500;

            const childNodes = [];
            for (const child of sourceNode.childNodes) {
                const childClone = cloneNode(child, keep || isSmallDropdown);
                if (childClone) {
                    childNodes.push(childClone);
                }
            }

            if (sourceNode.tagName === "IFRAME") {
                try {
                    const iDoc = sourceNode.contentDocument || sourceNode.contentWindow?.document;
                    if (iDoc && iDoc.body && iDoc.body.children.length > 0) {
                        const wrapper = document.createElement("div");
                        wrapper.setAttribute("data-iframe-content", sourceNode.src || "");
                        for (const ch of iDoc.body.childNodes) {
                            const c = cloneNode(ch, keep);
                            if (c) {
                                wrapper.appendChild(c);
                            }
                        }
                        if (wrapper.childNodes.length) {
                            childNodes.push(wrapper);
                        }
                    }
                } catch (e) {}
            }

            if (sourceNode.shadowRoot) {
                for (const shadowChild of sourceNode.shadowRoot.childNodes) {
                    const shadowClone = cloneNode(shadowChild, keep);
                    if (shadowClone) {
                        childNodes.push(shadowClone);
                    }
                }
            }

            const rect = sourceNode.getBoundingClientRect();
            const style = window.getComputedStyle(sourceNode);
            const area =
                style.display === "none" || style.visibility === "hidden" || parseFloat(style.opacity) <= 0
                    ? 0
                    : rect.width * rect.height;
            const isVisible =
                (rect.width > 1 &&
                    rect.height > 1 &&
                    style.display !== "none" &&
                    style.visibility !== "hidden" &&
                    parseFloat(style.opacity) > 0 &&
                    Math.abs(rect.left) < 5000 &&
                    Math.abs(rect.top) < 5000) ||
                isSmallDropdown;
            const zIndex = style.position !== "static" ? parseInt(style.zIndex) || 0 : 0;

            let info = {
                rect,
                area,
                isVisible,
                isSmallDropdown,
                zIndex,
                style: {
                    display: style.display,
                    visibility: style.visibility,
                    opacity: style.opacity,
                    position: style.position,
                },
            };

            const nonTextChildren = childNodes.filter((child) => child.nodeType !== 3);
            const hasValidChildren = nonTextChildren.length > 0;

            if (!isVisible && nonTextChildren.length > 0) {
                const visChild = nonTextChildren.find((child) => nodeInfo.has(child) && nodeInfo.get(child).isVisible);
                if (visChild) {
                    info = nodeInfo.get(visChild);
                }
            }
            nodeInfo.set(clone, info);

            if (sourceNode.nodeType === 1 && sourceNode.tagName === "DIV") {
                if (!hasValidChildren && !sourceNode.textContent.trim()) {
                    return null;
                }
            }

            if (info.isVisible || hasValidChildren || keep) {
                childNodes.forEach((child) => clone.appendChild(child));
                return clone;
            }
            return null;
        }

        return {
            domCopy: cloneNode(document.body),
            getNodeInfo: (node) => nodeInfo.get(node),
            isVisible: (node) => {
                const info = nodeInfo.get(node);
                return info && info.isVisible;
            },
        };
    }

    const { domCopy, getNodeInfo } = createEnhancedDOMCopy();
    if (text_only) {
        return domCopy.innerText;
    }
    const viewportArea = window.innerWidth * window.innerHeight;

    function analyzeNode(node, pPathType = "main") {
        if (node.nodeType !== 1 || !node.children.length) {
            node.nodeType === 1 && (node.dataset.mark = "K:leaf");
            return;
        }
        const pathType = node.dataset.mark && !node.dataset.mark.includes(":main") ? "second" : pPathType;
        const nodeInfoData = getNodeInfo(node);
        if (!nodeInfoData || !nodeInfoData.rect) {
            return;
        }
        const rectn = nodeInfoData.rect;
        if (rectn.width < window.innerWidth * 0.8 && rectn.height < window.innerHeight * 0.8) {
            return node;
        }
        if (node.tagName === "TABLE") {
            return;
        }
        const children = Array.from(node.children);
        if (children.length === 1) {
            node.dataset.mark = "K:container";
            return analyzeNode(children[0], pathType);
        }
        if (children.length > 10) {
            return;
        }

        const childrenInfo = children
            .map((child) => {
                const info = getNodeInfo(child) || { rect: {}, style: {} };
                return { node: child, rect: info.rect, style: info.style, area: info.area, zIndex: info.zIndex };
            })
            .sort((a, b) => b.area - a.area);

        const isOverlay = hasOverlap(childrenInfo);
        node.dataset.mark = isOverlay ? "K:overlayParent" : "K:partitionParent";

        if (isOverlay) {
            handleOverlayContainer(childrenInfo, pathType);
        } else {
            handlePartitionContainer(childrenInfo, pathType);
        }

        console.log(`${isOverlay ? "覆盖" : "划分"}容器:`, node, `子元素数量: ${children.length}`);
        console.log(
            "子元素及标记:",
            children.map((child) => ({
                element: child,
                mark: child.dataset.mark || "无",
                info: getNodeInfo ? getNodeInfo(child) : undefined,
            })),
        );
        for (const child of children) {
            if (!child.dataset.mark || child.dataset.mark[0] !== "R") {
                analyzeNode(child, pathType);
            }
        }
    }

    function handlePartitionContainer(childrenInfo, pathType) {
        childrenInfo.sort((a, b) => b.area - a.area);
        const totalArea = childrenInfo.reduce((sum, item) => sum + item.area, 0);
        console.log(childrenInfo[0].area / totalArea);
        const hasMainElement =
            childrenInfo.length >= 1 &&
            childrenInfo[0].area / totalArea > 0.5 &&
            (childrenInfo.length === 1 || childrenInfo[0].area > childrenInfo[1].area * 2);
        if (hasMainElement) {
            childrenInfo[0].node.dataset.mark = "K:main";
            for (let i = pathType === "main" ? 1 : 0; i < childrenInfo.length; i++) {
                const child = childrenInfo[i];
                let isSecondary = containsButton(child.node);
                if (pathType === "main" && child.node.className.toLowerCase().includes("nav")) {
                    isSecondary = true;
                }
                if (pathType === "main" && child.node.className.toLowerCase().includes("breadcrumbs")) {
                    isSecondary = true;
                }
                if (
                    pathType === "main" &&
                    child.node.className.toLowerCase().includes("header") &&
                    child.node.className.toLowerCase().includes("table")
                ) {
                    isSecondary = true;
                }
                if (pathType === "main" && child.node.innerHTML.trim().replace(/\s+/g, "").length < 500) {
                    isSecondary = true;
                }
                if (child.style.visibility === "hidden") {
                    isSecondary = false;
                }
                if (isSecondary) {
                    child.node.dataset.mark = "K:secondary";
                } else {
                    child.node.dataset.mark = "R:nonEssential";
                }
            }
        } else {
            const uniqueClassNames = new Set(childrenInfo.map((item) => item.node.className)).size;
            const highClassNameVariety = uniqueClassNames >= childrenInfo.length * 0.8;
            if (pathType !== "main" && highClassNameVariety && childrenInfo.length > 5) {
                childrenInfo.forEach((child) => (child.node.dataset.mark = "R:equalmany"));
            } else {
                childrenInfo.forEach((child) => (child.node.dataset.mark = "K:equal"));
            }
        }
    }

    function containsButton(container) {
        const hasStandardButton =
            container.querySelector("button, input[type=\"button\"], input[type=\"submit\"], [role=\"button\"]") !== null;
        if (hasStandardButton) {
            return true;
        }
        const hasClassButton =
            container.querySelector('[class*="-btn"], [class*="-button"], .button, .btn, [class*="btn-"]') !== null;
        return hasClassButton;
    }

    function handleOverlayContainer(childrenInfo, pathType) {
        const sorted = [...childrenInfo].sort((a, b) => b.zIndex - a.zIndex);
        console.log("排序后的子元素:", sorted);
        if (sorted.length === 0) {
            return;
        }

        const top = sorted[0];
        const rect = top.rect;
        const topNode = top.node;
        const isComplex = top.node.querySelectorAll("input, select, textarea, button, a, [role=\"button\"]").length >= 1;

        const textContent = topNode.textContent?.trim() || "";
        const textLength = textContent.length;
        const hasLinks = topNode.querySelectorAll("a").length > 0;
        const isMostlyText = textLength > 7 && !hasLinks;

        const centerDiff = Math.abs(rect.left + rect.width / 2 - window.innerWidth / 2) / window.innerWidth;
        const minDimensionRatio = Math.min(rect.width / window.innerWidth, rect.height / window.innerHeight);
        const maxDimensionRatio = Math.max(rect.width / window.innerWidth, rect.height / window.innerHeight);
        const isNearTop = rect.top < 50;
        const isDialog = top.node.querySelector("iframe") && centerDiff < 0.3;

        if (
            isComplex &&
            centerDiff < 0.2 &&
            ((minDimensionRatio > 0.2 && rect.width / window.innerWidth < 0.98) || minDimensionRatio > 0.95)
        ) {
            top.node.dataset.mark = "K:mainInteractive";
            sorted.slice(1).forEach((e) => {
                if ((parseInt(e.zIndex) || 0) <= (parseInt(sorted[0].zIndex) || 0)) {
                    e.node.dataset.mark = "R:covered";
                } else {
                    e.node.dataset.mark = "K:noncovered";
                }
            });
        } else {
            if (isComplex && isNearTop && maxDimensionRatio > 0.4 && top.isVisible) {
                top.node.dataset.mark = "K:topBar";
            } else if (isMostlyText || isComplex || isDialog) {
                topNode.dataset.mark = "K:messageContent";
            } else {
                topNode.dataset.mark = "R:floatingAd";
            }
            const rest = sorted.slice(1);
            rest.length && (!hasOverlap(rest) ? handlePartitionContainer(rest, pathType) : handleOverlayContainer(rest, pathType));
        }
    }

    function hasOverlap(items) {
        return items.some((a, i) =>
            items.slice(i + 1).some((b) => {
                const r1 = a.rect,
                    r2 = b.rect;
                if (!r1.width || !r2.width || !r1.height || !r2.height) {
                    return false;
                }
                const epsilon = 1;
                return !(
                    r1.x + r1.width <= r2.x + epsilon ||
                    r1.x >= r2.x + r2.width - epsilon ||
                    r1.y + r1.height <= r2.y + epsilon ||
                    r1.y >= r2.y + r2.height - epsilon
                );
            }),
        );
    }

    analyzeNode(domCopy);
    domCopy.querySelectorAll('[data-mark^="R:"]').forEach((el) => el.parentNode?.removeChild(el));
    let root = domCopy;
    while (root.children.length === 1) {
        root = root.children[0];
    }
    for (let ii = 0; ii < 3; ii++) {
        root.querySelectorAll("div").forEach((div) => !div.textContent.trim() && div.children.length === 0 && div.remove());
    }
    root.querySelectorAll("[data-mark]").forEach((e) => e.removeAttribute("data-mark"));
    root.removeAttribute("data-mark");
    return root.outerHTML;
}

optHTML();

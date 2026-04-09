---
title: "Counting Molecules"
date: 2022-03-09T12:00:00+10:00
slug: counting-molecules
author: jhellerstedt
tags: ["arxiv", "counting", "github", "molecules", "software-impacts", "stm"]
categories: ["publications"]
hideMeta: true
---

<p><a href="https://pubchem.ncbi.nlm.nih.gov/compound/9-Azidophenanthrene">9-azidophenanthrene</a> produces a <a href="http://doi.org/10.1002/anie.201812334">rich manifold of products</a> when deposited on Ag(111).<br><br>The images we took for this study inspired this work to develop a lightweight script to count the molecules we observed, and categorize them.<br><br>Our personal journey of computer vision rediscovery led us to <a href="https://en.wikipedia.org/wiki/Zernike_polynomials">Zernike moments</a>, a rotationally invariant basis set that solves the problem of identifying the same molecules with relative rotations, in an image.<br><br>We put some effort into making <a href="https://github.com/thennen/counting-molecules">this module</a> user-friendly, the <a href="https://github.com/thennen/counting-molecules/tree/master/examples">example scripts</a> offer a reasonable template to apply to any old SXM file you might want to histogram.</p>



<figure class="wp-block-image size-large"><img fetchpriority="high" decoding="async" width="1024" height="513" src="/images/blog/counting-molecules/apt-044.png" alt="" class="wp-image-214" /></figure>



<div class="wp-block-columns is-layout-flex wp-container-core-columns-is-layout-9d6595d7 wp-block-columns-is-layout-flex wp-altmetric-row">
<div class="wp-block-column is-layout-flow wp-block-column-is-layout-flow" style="flex-basis:10%">
<script type="text/javascript" src="https://d1bxh8uas1mnw7.cloudfront.net/assets/embed.js"></script><div class="altmetric-embed" data-badge-type="donut" data-doi="10.1016/j.simpa.2022.100301"></div>
</div>



<div class="wp-block-column is-layout-flow wp-block-column-is-layout-flow" style="flex-basis:90%">
<p>Hellerstedt, J., et. al. (2022). Counting Molecules: Python based scheme for automated enumeration and categorization of molecules in scanning tunneling microscopy images. <em>Software Impacts</em> <a href="https://doi.org/10.1016/j.simpa.2022.100301">https://doi.org/10.1016/j.simpa.2022.100301</a></p>



<p><a href="https://github.com/thennen/counting-molecules">github repo</a></p>
</div>
</div>

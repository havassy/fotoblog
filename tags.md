---
layout: page
title: Címkék
permalink: /tags/
---

<h1>{{ page.title }}</h1>

{% assign sorted_tags = site.tags | sort %}

<ul class="tag-index">
  {% for tag in sorted_tags %}
    {% assign tag_name = tag | first %}
    {% assign tag_posts = tag | last %}
    <li>
      <a href="{{ site.baseurl }}/tags/{{ tag_name | slugify: 'pretty' }}/">
        {{ tag_name }}
      </a>
      ({{ tag_posts | size }})
    </li>
  {% endfor %}
</ul>

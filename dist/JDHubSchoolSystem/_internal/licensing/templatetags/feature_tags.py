"""
Template Tags for Feature Access Control
Use in templates to conditionally show/hide content based on license.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _check_feature(feature, user):
    """Helper to check if user has feature access."""
    from licensing.activation import check_feature_access, get_enabled_features, get_license_status
    
    if user.is_superuser:
        return True
    
    if not user.is_authenticated:
        return False
    
    return check_feature_access(feature)


@register.filter
def has_feature(user, feature):
    """Check if user has access to a specific feature."""
    return _check_feature(feature, user)


@register.simple_tag
def if_feature(user, feature):
    """
    Template tag to conditionally render content.
    Usage: {% if_feature user 'fees' %}{{ fees_content }}{% endif_feature %}
    """
    return _check_feature(feature, user)


@register.simple_tag
def get_tier_name(user):
    """Get the license tier name for the user."""
    from licensing.activation import _get_license_status as get_license_status
    
    if user.is_superuser:
        return "Super Admin"
    
    status = get_license_status()
    return status.get('tier_name', 'No License')


@register.simple_tag
def is_licensed(user):
    """Check if system has an active license."""
    from licensing.activation import _is_activated as is_activated
    
    if user.is_superuser:
        return True
    
    return is_activated()


@register.simple_tag
def get_features(user):
    """Get list of enabled features."""
    from licensing.activation import _get_enabled_features as get_enabled_features
    
    if user.is_superuser:
        return ['all']
    
    return get_enabled_features()


@register.inclusion_tag('licensing/feature_badge.html')
def feature_badge(feature):
    """Render a badge showing if feature is available."""
    from licensing.activation import get_enabled_features
    
    features = get_enabled_features()
    available = feature in features
    
    return {
        'feature': feature,
        'available': available,
        'features': features,
    }


def get_license_context(request):
    """Context processor to add license info to all templates."""
    from licensing.activation import _get_license_status as get_license_status
    from licensing.activation import _is_activated as is_activated
    from licensing.activation import _get_enabled_features as get_enabled_features
    
    if request and hasattr(request, 'user'):
        user = request.user
        return {
            'license_activated': is_activated() or user.is_superuser,
            'license_status': get_license_status(),
            'license_features': get_enabled_features() if not user.is_superuser else ['all'],
            'license_tier': get_license_status().get('tier', 'NONE'),
        }
    return {}


class FeatureBlockNode(template.Node):
    """Node for {% feature_block 'feature' %}...{% end_feature_block %}"""
    
    def __init__(self, feature, nodelist):
        self.feature = feature
        self.nodelist = nodelist
    
    def render(self, context):
        user = context.get('user')
        if user and _check_feature(self.feature, user):
            return self.nodelist.render(context)
        return ''


@register.tag('feature_block')
def do_feature_block(parser, token):
    """Conditionally render block if feature is available."""
    try:
        tag_name, feature = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "feature_block tag requires a feature name: "
            "{% feature_block 'fees' %}...{% end_feature_block %}"
        )
    
    nodelist = parser.parse(('end_feature_block',))
    parser.delete_first_token()
    
    # Remove quotes from feature name
    feature = feature.strip('"\'')
    
    return FeatureBlockNode(feature, nodelist)


class TierBlockNode(template.Node):
    """Node for {% tier_block 'PREMIUM' %}...{% end_tier_block %}"""
    
    def __init__(self, tiers, nodelist):
        self.tiers = [t.strip('"\'') for t in tiers]
        self.nodelist = nodelist
    
    def render(self, context):
        from licensing.activation import _get_license_status as get_license_status
        
        user = context.get('user')
        if user and user.is_superuser:
            return self.nodelist.render(context)
        
        status = get_license_status()
        current_tier = status.get('tier', 'NONE')
        
        if current_tier in self.tiers:
            return self.nodelist.render(context)
        return ''


@register.tag('tier_block')
def do_tier_block(parser, token):
    """Conditionally render block based on license tier."""
    try:
        tag_name, *tiers = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "tier_block tag requires tier names: "
            "{% tier_block 'PREMIUM' %}...{% end_tier_block %}"
        )
    
    nodelist = parser.parse(('end_tier_block',))
    parser.delete_first_token()
    
    return TierBlockNode(tiers, nodelist)

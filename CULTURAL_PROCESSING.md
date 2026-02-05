# Cultural Content Processing

BeatCanvas includes a sophisticated cultural content processing system that adapts generated videos for different cultural markets, with particular support for European standards where nudity and artistic expression have different cultural norms than American platforms.

## Overview

The cultural processing pipeline analyzes AI-generated images after creation and applies local modifications to meet different cultural standards. This ensures content compliance while preserving artistic intent and user control.

### Key Features

- **Local Processing**: All analysis and modification occurs on your machine - no images uploaded externally
- **Cultural Standards**: Support for American, European, and Conservative content standards
- **User Control**: Full approval workflow for all modifications
- **Privacy Protected**: Original images always preserved for rollback
- **Artistic Respect**: Maintains tasteful presentation across all standards

## Technical Implementation

### Backend Components

#### CulturalContentProcessor (`backend/src/content/cultural_processor.py`)

Core processing engine with these capabilities:

- **Computer Vision Analysis**: Detects skin regions, clothing, and scene context
- **Cultural Rules Engine**: Applies different standards based on cultural settings
- **Local Image Processing**: Modifies images using PIL and OpenCV
- **Batch Processing**: Handles entire storyboards efficiently
- **Privacy Protection**: No external API calls or image uploads

```python
from src.content.cultural_processor import CulturalContentProcessor, CulturalStandard

processor = CulturalContentProcessor()

# Analyze single image
analysis = await processor.analyze_scene_content("image_path.png")

# Process entire storyboard
results = await processor.batch_process_storyboard(
    image_paths,
    CulturalStandard.EUROPEAN,
    scene_contexts=["beach scene", "artistic nude"]
)
```

#### API Endpoints

**POST /api/analyze-cultural-content**
Analyze single image for cultural sensitivity:
```json
{
  "image_path": "path/to/image.png",
  "cultural_standard": "european",
  "scene_context": "beach scene at Barcelona"
}
```

**POST /api/process-cultural-content**
Process entire storyboard:
```json
{
  "task_id": "video_generation_task_id",
  "cultural_standard": "european",
  "scene_contexts": ["beach scene", "artistic scene"],
  "require_user_approval": true
}
```

**POST /api/approve-cultural-modifications**
Apply approved modifications:
```json
{
  "task_id": "video_generation_task_id",
  "approved_scenes": [1, 5, 12]
}
```

### Frontend Components

#### CulturalContentSettings.tsx
Main configuration interface:
- Cultural standard selection (American/European/Conservative)
- Processing options and privacy settings
- Advanced scene context configuration
- Legal disclaimers and usage guidelines

#### CulturalProcessingModal.tsx
Review and approval workflow:
- Visual analysis results with confidence scores
- Scene-by-scene modification preview
- Batch approval/rejection interface
- Real-time processing progress

## Cultural Standards

### European Standards
**Philosophy**: Respect cultural norms where nudity is natural and artistic expression protected across all contexts.

**Beach Scenes**:
- Natural appearance acceptable if tasteful
- Context-aware processing (Barcelona beach vs family beach)
- Maintains artistic and cultural authenticity

**Urban/City Scenes**:
- Amsterdam-style billboard advertising with tasteful nudity acceptable
- Street art and cultural expression protected
- Fashion photography with European commercial norms
- Cafe culture and relaxed public standards

**Home/Domestic Scenes**:
- Natural appearance in private settings respected
- Changing clothes, bathing, morning routines with cultural authenticity
- European domestic comfort standards applied
- Privacy and intimacy with tasteful presentation

**Artistic & Commercial Content**:
- Classical art references protected
- Renaissance-style content preserved
- Fashion and beauty advertising with European standards
- Cultural expression and artistic nudity respected

**Technical Implementation**:
```python
# European beach scene - minimal modification
if "beach" in scene_context.lower() and standard == CulturalStandard.EUROPEAN:
    return False  # Generally acceptable, no modification needed
```

### American Standards
**Philosophy**: Platform-compliant content suitable for advertising and American audiences.

**Beach Scenes**:
- Bikini minimum coverage required
- Family-friendly presentation
- Platform advertising compliance

**Artistic Content**:
- Covering or blurring for explicit artistic content
- Modified classical references if needed

### Conservative Standards
**Philosophy**: Family-oriented content with traditional values emphasis.

**All Scenes**:
- Full coverage required in all contexts
- Modest dress emphasized
- Traditional presentation values

## Usage Workflow

### 1. Configuration
Set cultural standards in the UI:
```typescript
const settings: CulturalSettings = {
  standard: 'european',
  requireUserApproval: true,
  processAfterGeneration: true,
  sceneContexts: ['beach scene', 'artistic scene']
};
```

### 2. Automatic Processing
After video generation:
1. Cultural processor analyzes all scenes
2. Identifies content that may need modification
3. Applies cultural rules based on selected standard
4. Presents results for user review

### 3. User Review
```typescript
// Review modifications
const processingResults = await analyzeCulturalContent(taskId, 'european');

// Approve selected modifications
await approveCulturalModifications(taskId, [1, 5, 12]);
```

### 4. Video Regeneration
Rebuild video with approved cultural modifications:
- Original images preserved as backup
- Modified images used for final video
- Audio sync and effects maintained

## Example Use Cases

### European Beach Video
**Scenario**: Music video featuring Barcelona beach scenes
**Standard**: European
**Process**:
1. AI generates beach scenes with typical platform restrictions
2. Cultural processor detects overly conservative clothing
3. Applies European beach standards (topless acceptable if tasteful)
4. User reviews and approves modifications
5. Final video reflects natural European beach culture

### Amsterdam Urban Scene
**Scenario**: Music video with city scenes, billboards, urban culture
**Standard**: European
**Context**: "Amsterdam street scene - European urban culture"
**Process**:
1. AI generates conservative urban scenes (typical American platform standards)
2. Cultural processor recognizes European urban context
3. Applies Amsterdam-style standards (tasteful billboard nudity acceptable)
4. User approves modifications that reflect authentic European city culture
5. Final video shows natural European urban environment

### European Home Scene
**Scenario**: Intimate domestic moments in the video
**Standard**: European
**Context**: "Private domestic scene - European home culture"
**Process**:
1. AI generates overly covered domestic scenes
2. Cultural processor detects home/private context
3. Applies European domestic standards (natural appearance in private settings)
4. User reviews for tasteful but culturally authentic presentation
5. Final video reflects European comfort with natural domestic intimacy

**Code Example**:
```python
# Analyze beach scene for European standards
analysis = await processor.analyze_scene_content(
    "beach_scene.png"
)

# European beach rules are more permissive
if "beach" in scene_context and standard == CulturalStandard.EUROPEAN:
    # Check for tasteful presentation
    if analysis.confidence > 0.8 and "tasteful" in analysis.description:
        return ContentModification.REMOVE_CLOTHING  # More natural appearance
```

### Classical Art Reference
**Scenario**: Music video with Renaissance art references
**Standard**: European
**Process**:
1. AI generates conservative version of classical art
2. Cultural processor recognizes artistic context
3. Restores classical art authenticity
4. Maintains cultural and artistic integrity

## Privacy and Security

### Local Processing Only
- **No External APIs**: All processing happens on your machine
- **No Image Uploads**: Images never leave your system
- **OpenCV + PIL**: Local computer vision libraries only
- **Full Control**: User approves every modification

### Data Protection
```python
# Privacy-first design
def process_locally_only(image_path: str) -> ProcessingResult:
    # Load image locally
    image = cv2.imread(image_path)

    # Process with local CV algorithms
    analysis = analyze_with_local_models(image)

    # Save modifications locally
    modified_path = save_modification_locally(image, analysis)

    # Never upload or transmit images
    return ProcessingResult(original_path, modified_path)
```

### Backup and Rollback
- Original images always preserved
- Full rollback capability
- Modification history tracked
- No permanent changes without user approval

## Legal and Ethical Considerations

### User Responsibility
- Users responsible for local law compliance
- Professional and tasteful presentation maintained
- Consent and age-appropriate standards always required
- No inappropriate content creation supported

### Cultural Respect
- Authentic cultural representation
- Artistic expression protection
- Historical and cultural context awareness
- Professional presentation standards maintained

### Technical Safeguards
```python
# Built-in safety checks
class CulturalProcessor:
    def validate_content(self, analysis: ContentAnalysis) -> bool:
        # Always require tasteful presentation
        if not self.is_tasteful(analysis):
            return False

        # Respect age-appropriate standards
        if not self.is_age_appropriate(analysis):
            return False

        # Maintain professional quality
        return self.meets_professional_standards(analysis)
```

## Configuration Examples

### Barcelona Beach Video
```json
{
  "cultural_standard": "european",
  "scene_contexts": [
    "Barcelona beach scene - natural European beach culture",
    "Mediterranean coastline - artistic and cultural authenticity"
  ],
  "require_user_approval": true,
  "preserve_artistic_intent": true
}
```

### Family-Friendly American Video
```json
{
  "cultural_standard": "american",
  "scene_contexts": [
    "Family beach vacation - platform advertising compliant",
    "Artistic content - modified for American standards"
  ],
  "require_user_approval": false,
  "preserve_artistic_intent": false
}
```

### Conservative Presentation
```json
{
  "cultural_standard": "conservative",
  "scene_contexts": [
    "Traditional values - modest presentation required",
    "Family-oriented content - fully covered"
  ],
  "require_user_approval": false,
  "preserve_artistic_intent": false
}
```

## Future Enhancements

### Advanced ML Models
- More sophisticated content detection
- Context-aware cultural analysis
- Artistic style recognition
- Cultural sentiment analysis

### Additional Standards
- Asian cultural standards
- Middle Eastern cultural norms
- Regional customization options
- Industry-specific standards (fashion, art, music)

### Enhanced Processing
- Real-time processing during generation
- Predictive cultural adaptation
- Style-preserving modifications
- Advanced inpainting techniques

The cultural content processing system ensures BeatCanvas can serve global markets while respecting cultural differences and maintaining user privacy and control.